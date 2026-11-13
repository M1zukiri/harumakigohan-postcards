# 2026-10-27 22:40:00 Futarino2 八个提取任务：纯黑白线稿贴纸
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers_f2")
REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f2")
os.makedirs(OUT, exist_ok=True)
os.makedirs(REVIEW, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def imread(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)


def load_job(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    bgr = imread(os.path.join(TASKS, j["image_file"]))
    r = j["rect"]
    h, w = bgr.shape[:2]
    x0 = max(0, r["x"]); y0 = max(0, r["y"])
    x1 = min(w, r["x"] + r["w"]); y1 = min(h, r["y"] + r["h"])
    return j, bgr[y0:y1, x0:x1].copy(), (x0, y0, x1, y1)


def save_rgba(path, alpha, scale=1.0, soft=False, binarize_thr=40, min_area=45):
    """soft=True 时保留灰度 alpha（线宽与深浅都在），只清掉极淡的底噪。"""
    if scale != 1.0:
        interp = cv2.INTER_LANCZOS4 if soft else cv2.INTER_CUBIC
        alpha = cv2.resize(alpha, None, fx=scale, fy=scale, interpolation=interp)
    alpha = np.asarray(alpha, np.float32)
    if soft:
        a = np.clip(alpha, 0, 255)
        a[a < 6] = 0
    else:
        a = np.clip(alpha, 0, 255).astype(np.uint8)
        a = keep_components(a > binarize_thr, min_area).astype(np.uint8) * 255
    ys, xs = np.nonzero(a > 8)
    if len(xs) == 0:
        raise RuntimeError("empty result")
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    a = a[box[1]:box[3], box[0]:box[2]]
    if soft:
        a = a.astype(np.uint8)
    rgb = np.zeros((a.shape[0], a.shape[1], 3), np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)
    return a.shape[1], a.shape[0]


def keep_components(binary, min_area=8):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), 8)
    out = np.zeros_like(binary, np.uint8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            out[lab == i] = 1
    return out.astype(bool)


# ---------- 暗底亮的线稿（门、文字、标识） ----------
def glow_lines(roi, thr=70, sat_max=255, min_area=10, thick=1):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    S = hsv[..., 1].astype(np.int16)
    V = hsv[..., 2].astype(np.int16)
    m = (V > thr) & (S <= sat_max)
    m = keep_components(m, min_area)
    a = (m * 255).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    if thick > 1:
        a = cv2.dilate(a, np.ones((2, 2), np.uint8), iterations=thick - 1)
    return a.astype(np.float32)


def t_221752():
    """门形图案：黑底霓虹描边，本身就是线稿。"""
    j, roi, box = load_job("T20261027_221752")
    a = glow_lines(roi, thr=52, min_area=6, thick=1)
    p = os.path.join(OUT, "F2_门.png")
    w, h = save_rgba(p, a)
    return p, "T571752 门形图案", (w, h)


def t_222011():
    """「秘密」两个字。"""
    j, roi, box = load_job("T20261027_222011")
    a = glow_lines(roi, thr=52, min_area=6, thick=1)
    p = os.path.join(OUT, "F2_秘密.png")
    w, h = save_rgba(p, a, 1.6)
    return p, "T582011 秘密", (w, h)


def t_222028():
    """Studio Gohan 标识；彩色花瓣靠饱和度剔掉。"""
    j, roi, box = load_job("T20261027_222028")
    a = glow_lines(roi, thr=55, sat_max=150, min_area=8, thick=2)
    p = os.path.join(OUT, "F2_StudioGohan.png")
    w, h = save_rgba(p, a, 1.4)
    return p, "T582028 StudioGohan", (w, h)



def contour_alpha(mask, width=3, ss=4):
    """掩膜外轮廓画等宽线，4 倍超采样去阶梯。"""
    if isinstance(mask, np.ndarray) and mask.dtype != bool:
        mask = mask > 0.5
    h, w = mask.shape
    big = cv2.resize((mask.astype(np.uint8)) * 255, (w * ss, h * ss), interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.6)
    big = (big > 127).astype(np.uint8)
    cnts, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    line = np.zeros((h * ss, w * ss), np.uint8)
    cv2.drawContours(line, cnts, -1, 255, max(1, int(width * ss)), cv2.LINE_AA)
    line = cv2.resize(line, (w, h), interpolation=cv2.INTER_AREA)
    return line.astype(np.float32)


def grabcut_center(roi, iters=6, fg_shrink=0.55, bg_margin=0.05):
    h, w = roi.shape[:2]
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    mh, mw = max(2, int(h * bg_margin)), max(2, int(w * bg_margin))
    gc[:mh, :] = cv2.GC_BGD; gc[-mh:, :] = cv2.GC_BGD
    gc[:, :mw] = cv2.GC_BGD; gc[:, -mw:] = cv2.GC_BGD
    ch, cw = int(h * fg_shrink), int(w * fg_shrink)
    y0 = (h - ch) // 2; x0 = (w - cw) // 2
    gc[y0:y0 + ch, x0:x0 + cw] = cv2.GC_PR_FGD
    bgm = np.zeros((1, 65), np.float64); fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(roi, gc, None, bgm, fgm, iters, cv2.GC_INIT_WITH_MASK)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    return ndimage.binary_fill_holes(m)


def inner_dog(roi, mask, sigma=7, t1=6.0, t2=26.0):
    """局部暗线（角色描边、褶皱）：比周边暗的细结构。"""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), sigma)
    dog = blur - gray
    line = np.clip((dog - t1) / max(t2 - t1, 1e-3), 0, 1)
    return line * (mask.astype(np.float32))


def stroke_art(roi, mask, sigma=7, t1=6.0, t2=26.0, outer_w=2, outer_k=0.9, norm_w=0):
    inner = inner_dog(roi, mask, sigma, t1, t2)
    outer = contour_alpha(mask, outer_w)
    comb = np.clip(np.maximum(inner, outer * outer_k), 0, 1)
    if norm_w > 0:
        from skimage.morphology import skeletonize
        b = (comb > 0.35).astype(np.uint8)
        b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
        sk = skeletonize(b)
        comb = cv2.dilate(sk.astype(np.uint8) * 255, np.ones((norm_w, norm_w), np.uint8)).astype(np.float32) / 255.0
    return comb


def person_sticker(tid, out_name, label, shrink=0.55, bgm=0.05, sigma=7.0, t1=6.0, t2=26.0):
    j, roi, box = load_job(tid)
    mask = grabcut_center(roi, fg_shrink=shrink, bg_margin=bgm)
    line = stroke_art(roi, mask, sigma, t1, t2, norm_w=2)
    p = os.path.join(OUT, out_name)
    w, h = save_rgba(p, line * 255)
    return p, label, (w, h)

# ---------- 人物 / 物体：先抠主体，再抽线 ----------
def cut_subject(roi):
    rgb = roi[:, :, ::-1]
    try:
        from ai_cutout import predict_alpha
        a = predict_alpha(rgb)
        m = a > 0.5
        if m.sum() > m.size * 0.02:
            return a, "ai"
    except Exception as e:
        sys.stderr.write("ai skip: %s\n" % e)
    return None, "none"


def line_from_mask(roi, mask, lo=45, hi=115, thick=1):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(gray, (0, 0), 1.0)
    e = cv2.Canny(g, lo, hi)
    inside = cv2.erode((mask > 0.5).astype(np.uint8) * 255, np.ones((3, 3), np.uint8)) > 0
    e = e.astype(bool) & inside
    a = (e * 255).astype(np.uint8)
    if thick > 1:
        a = cv2.dilate(a, np.ones((2, 2), np.uint8), iterations=thick - 1)
    return a.astype(np.float32)


def t_221819():
    """T571819 人物轮廓（红天幕下的小角色，剪影风格）。"""
    return person_sticker("T20261027_221819", "F2_人物A.png", "T571819 人物A", 0.5, 0.04)

def t_222000():
    """T582000 人物（王冠长发角色）。"""
    return person_sticker("T20261027_222000", "F2_人物B.png", "T582000 人物B", 0.7, 0.03, sigma=3.5, t1=8, t2=30)


def t_221905():
    """T571905 双角色。"""
    return person_sticker("T20261027_221905", "F2_双角色.png", "T571905 双角色", 0.6, 0.03, sigma=3.5, t1=8, t2=30)


def t_221855():
    """地球仪：蓝球 + 金支架，保留球面经线，排除底部阴影与背景放射线。"""
    j, roi, box = load_job("T20261027_221855")
    rgb = roi[:, :, ::-1]
    R, G, B = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    blue = (B > 150) & (B > R + 60)
    gold = (R > 135) & (G > 75) & (B < 130) & (R > B + 60)
    m = blue | gold
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, [i + 1 for i in range(n) if sizes[i] > 400])
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    m[:int(m.shape[0]*0.02), :] = False
    m = ndimage.binary_opening(m, np.ones((5, 5)))
    line = stroke_art(roi, m, sigma=4.0, t1=4.0, t2=16.0, outer_w=2, outer_k=0.55, norm_w=2)
    p = os.path.join(OUT, "F2_地球仪.png")
    w, h = save_rgba(p, line * 255)
    return p, "T571855 地球仪", (w, h)

def t_221950():
    """饭团：用工作台提交的手工蒙版（绿笔勾的轮廓）。"""
    from PIL import Image as _Img
    mid = "M20261027_223312"
    img = np.array(_Img.open(os.path.join(TASKS, mid + ".png")).convert("RGB"))
    mk = np.array(_Img.open(os.path.join(TASKS, mid + "_mask.png")).convert("RGBA"))
    painted = mk[..., 3] > 40
    keep = painted & (mk[..., 1] > 130) & (mk[..., 0] < 130)
    keep = ndimage.binary_closing(keep, np.ones((11, 11)))
    keep = ndimage.binary_fill_holes(keep)
    lab, n = ndimage.label(keep)
    if n:
        sizes = ndimage.sum(keep, lab, range(1, n + 1))
        keep = lab == (int(np.argmax(sizes)) + 1)
    keep = ndimage.binary_opening(keep, np.ones((5, 5)))
    line = contour_alpha(keep, 3, ss=4)
    p = os.path.join(OUT, "F2_饭团.png")
    w, h = save_rgba(p, line * 255)
    return p, "T581950 饭团", (w, h)

JOBS = {
    "221752": t_221752,
    "221819": t_221819,
    "221905": t_221905,
    "221950": t_221950,
    "221855": t_221855,
    "222000": t_222000,
    "222011": t_222011,
    "222028": t_222028,
}


def preview(items, dst, cols=3):
    tiles = []
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    for p, label, size in items:
        im = Image.open(p).convert("RGBA")
        W, H = im.size
        k = min(400 / W, 340 / H, 1.0)
        if k < 1:
            im = im.resize((max(1, int(W * k)), max(1, int(H * k))), Image.LANCZOS)
        pad = 14
        c = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2 + 22), (255, 255, 255, 255))
        c.alpha_composite(im, (pad, pad))
        ImageDraw.Draw(c).text((pad, im.height + pad + 2), f"{label}  {size[0]}x{size[1]}",
                               fill=(40, 40, 40), font=f)
        tiles.append(c.convert("RGB"))
    rows = (len(tiles) + cols - 1) // cols
    tw = max(t.width for t in tiles); th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (tw * cols, th * rows), (240, 240, 240))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    sheet.save(dst)
    return sheet.size


if __name__ == "__main__":
    keys = sys.argv[1:] or list(JOBS)
    items = []
    for k in keys:
        try:
            p, label, size = JOBS[k]()
            items.append((p, label, size))
            print("ok", os.path.basename(p), size)
        except Exception as e:
            print("FAIL", k, e)
            import traceback
            traceback.print_exc()
    if items:
        print(preview(items, os.path.join(REVIEW, "_preview.png")))
