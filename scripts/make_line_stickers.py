# 2026-10-27 01:40:00 把工作台截图里的元素抠成线稿贴纸（透明底 + 纯黑轮廓线）
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers")


def imread(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def save_rgba(path, rgb, alpha):
    rgba = np.dstack([rgb, alpha]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


def hsv_parts(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    rgb = bgr[:, :, ::-1]
    H = hsv[..., 0].astype(np.int16)
    S = hsv[..., 1].astype(np.int16)
    V = hsv[..., 2].astype(np.int16)
    R, G, B = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    return rgb, H, S, V, R, G, B


def contour_alpha(mask, width=3, ss=4):
    """取掩膜外轮廓画成等宽线条；4 倍超采样后再缩回，消掉像素阶梯。"""
    h, w = mask.shape
    big = cv2.resize(mask.astype(np.uint8) * 255, (w * ss, h * ss), interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 2.0)
    big = (big > 127).astype(np.uint8)
    cnts, _ = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    line = np.zeros((h * ss, w * ss), np.uint8)
    cv2.drawContours(line, cnts, -1, 255, max(1, width * ss), cv2.LINE_AA)
    line = cv2.resize(line, (w, h), interpolation=cv2.INTER_AREA)
    return line.astype(np.float32) / 255.0


def xdog_line(bgr, lo=30, hi=90, sigma=1.0):
    """Canny 边缘做线稿（适合实心剪影类素材）。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(gray, (0, 0), sigma)
    e = cv2.Canny(g, lo, hi)
    return (e > 0).astype(np.float32)


def thin_on_dark(bgr, thr=0.55):
    """对原本就是线稿的图：暗像素即线条。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    return np.clip((thr - gray) / thr, 0.0, 1.0)


def inner_lines(bgr, mask, detail, inset=9, min_len=8):
    """提取掩膜内部的原图线条（裙褶、分界等）。detail 0..1 控制灵敏度。"""
    if detail <= 0:
        return np.zeros(mask.shape, np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (0, 0), 1.0)
    lo = int(round(95 - 63 * detail))
    hi = int(round(190 - 120 * detail))
    e = cv2.Canny(gray, lo, hi)
    inner = e > 0
    # 只在离外轮廓 inset 像素以内的地方取线，避免和轮廓线并成双线
    core = cv2.erode(mask.astype(np.uint8), np.ones((inset, inset), np.uint8)) > 0
    inner &= core
    # 去掉短线头（噪点），保留成的线条
    lab, n = ndimage.label(inner, np.ones((3, 3)))
    if n:
        sizes = ndimage.sum(inner, lab, range(1, n + 1))
        inner = np.isin(lab, [i + 1 for i in range(n) if sizes[i] >= min_len])
    return inner.astype(np.float32)


def compose_lines(mask, bgr, width=3, detail=0.0, inset=9):
    """外轮廓 + 可选的内部线条。detail=0 只有外轮廓。"""
    line = contour_alpha(mask, width)
    if detail > 0:
        line = np.maximum(line, inner_lines(bgr, mask, detail, inset))
    return line


def grow_to_edges(line, mask, iters=2):
    """让线条在 mask 边缘处收口，避免断线。"""
    edge = mask & ~ndimage.binary_erosion(mask, np.ones((3, 3)))
    out = line.astype(np.float32)
    for _ in range(iters):
        out = np.maximum(out, cv2.dilate(out, np.ones((3, 3), np.uint8)) * edge)
    return out


def solidify(mask, close=5, min_area=300, max_hole=400):
    """闭运算 + 只填小洞（大洞是角色之间的天空，必须保留）+ 去碎块。"""
    m = ndimage.binary_closing(mask, np.ones((close, close)))
    solid = ndimage.binary_fill_holes(m)
    holes = solid & ~m
    labh, nh = ndimage.label(holes)
    if nh:
        hs = ndimage.sum(holes, labh, range(1, nh + 1))
        m = m | np.isin(labh, [i + 1 for i in range(nh) if hs[i] <= max_hole])
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, [i + 1 for i in range(n) if sizes[i] >= min_area])
    return m


def grabcut_mask(bgr, core, bg_hard, roi, iters=6):
    gc = np.full(bgr.shape[:2], cv2.GC_PR_BGD, np.uint8)
    gc[core] = cv2.GC_FGD
    gc[bg_hard] = cv2.GC_BGD
    gc[~roi] = cv2.GC_BGD
    bgm = np.zeros((1, 65), np.float64)
    fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc, None, bgm, fgm, iters, cv2.GC_INIT_WITH_MASK)
    return (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)


def make_lines_rgba(bgr, alpha_line, mask, line_w=3):
    """把线稿强度转成黑线 + 透明底。"""
    a = np.clip(alpha_line, 0, 1).astype(np.float32)
    if line_w > 1:
        a = cv2.dilate(a, np.ones((line_w - 1, line_w - 1), np.uint8))
    a = np.clip(a * 255.0, 0, 255).astype(np.uint8)
    rgb = np.zeros_like(bgr)
    ys, xs = np.nonzero(a > 10)
    if len(xs) == 0:
        return rgb, a
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    return rgb[box[1]:box[3], box[0]:box[2]], a[box[1]:box[3], box[0]:box[2]]


# ---------------- 任务 1：两个角色 + 脚下草地 ----------------
def task1(detail=0.0, width=3):
    from ai_cutout import predict_alpha

    bgr = imread(os.path.join(TASKS, "T20261027_005710.png"))
    rgb, H, S, V, R, G, B = hsv_parts(bgr)
    h, w = bgr.shape[:2]

    x0, y0, x1, y1 = 700, 290, 1240, 810
    a = predict_alpha(rgb[y0:y1, x0:x1])
    alpha = np.zeros((h, w), np.float32)
    alpha[y0:y1, x0:x1] = a

    body = alpha > 0.5
    # 外围轮廓交给 isnet（它判得准）；只在掩膜内部按颜色清理，把两腿之间、
    # 两人手臂之间的天空挖掉，避免削薄角色本身的边缘
    dark = (V < 165) & (B > G + 8) & (S > 100)
    near = cv2.dilate(dark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    inner = cv2.erode(body.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    body &= ~(inner & ~(dark | near))
    body = ndimage.binary_closing(body, np.ones((3, 3)))
    body = ndimage.binary_opening(body, np.ones((3, 3)))
    lab, n = ndimage.label(body)
    if n:
        sizes = ndimage.sum(body, lab, range(1, n + 1))
        body = np.isin(lab, [i + 1 for i in range(n) if sizes[i] > 200])

    ys, xs = np.nonzero(body)
    bx0, bx1, foot = xs.min(), xs.max(), ys.max()

    # 脚下草地带
    grass = (G > 140) & (R > 90) & ((G - B) > 50)
    yy = np.arange(h)[:, None]
    xx = np.arange(w)[None, :]
    gmask = grass & (yy >= foot - 8) & (yy <= foot + 30) & (xx >= bx0 - 4) & (xx <= bx1 + 4)
    gmask = ndimage.binary_closing(gmask, np.ones((1, 41)))
    gmask = ndimage.binary_closing(gmask, np.ones((5, 21)))
    gmask = ndimage.binary_opening(gmask, np.ones((3, 3)))
    labg, ng = ndimage.label(gmask)
    if ng:
        best = max(range(1, ng + 1), key=lambda i: (labg == i).sum())
        gmask = labg == best
        gmask = ndimage.binary_closing(gmask, np.ones((7, 21)))

    mask = solidify(body | gmask, 3, 200, 400)

    line = compose_lines(mask, bgr, width=width, detail=detail)

    out_rgb, out_a = make_lines_rgba(bgr, line, mask, 1)
    path = os.path.join(OUT, "Futarino1_T1_双人线稿.png")
    save_rgba(path, out_rgb, out_a)
    return path, dict(task="T20261027_005710", detail=detail, size=(out_a.shape[1], out_a.shape[0]))


# ---------------- 任务 2：俯视鲸鱼（非人物，isnet-anime 不适用，走颜色分割） ----------------
def task2():
    bgr = imread(os.path.join(TASKS, "T20261027_005724.png"))
    rgb, H, S, V, R, G, B = hsv_parts(bgr)
    h, w = bgr.shape[:2]

    roi = np.zeros((h, w), bool)
    roi[575:795, 800:1170] = True

    core = (S > 120) & (V < 165) & (B > G + 20) & roi
    core = ndimage.binary_closing(core, np.ones((7, 7)))
    lab, n = ndimage.label(core)
    sizes = ndimage.sum(core, lab, range(1, n + 1))
    core = lab == (int(np.argmax(sizes)) + 1)

    dcore = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    bg_hard = ((dcore > 8) & roi) | (~roi)

    mask = grabcut_mask(bgr, core, bg_hard, roi)
    mask = solidify(mask, 7, 500)

    line = contour_alpha(mask, 3)

    out_rgb, out_a = make_lines_rgba(bgr, line, mask, 1)
    path = os.path.join(OUT, "Futarino1_T2_鲸鱼线稿.png")
    save_rgba(path, out_rgb, out_a)
    return path, dict(task="T20261027_005724", size=(out_a.shape[1], out_a.shape[0]))


# ---------------- 任务 3：約束 两个字 ----------------
def task3():
    bgr = imread(os.path.join(TASKS, "T20261027_005825.png"))
    rgb, H, S, V, R, G, B = hsv_parts(bgr)

    x0, y0, x1, y1 = 832, 368, 1052, 482
    sub = bgr[y0:y1, x0:x1]
    Sr, Vr = S[y0:y1, x0:x1], V[y0:y1, x0:x1]
    Br, Gr = B[y0:y1, x0:x1], G[y0:y1, x0:x1]

    # 深蓝笔画（含三个圆点的描边）；奶黄填充与天空都不满足
    ink = (Vr < 178) & (Br > Gr + 8)
    ink = ndimage.binary_closing(ink, np.ones((3, 3)))
    line = ink.astype(np.float32)
    # 2 倍上采样输出，让线条在明信片尺寸下不糊
    line = cv2.resize(line, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    line = np.clip((line - 0.28) / 0.44, 0, 1)

    out_rgb = np.zeros((line.shape[0], line.shape[1], 3), np.uint8)
    out_a = (np.clip(line, 0, 1) * 255).astype(np.uint8)
    ys, xs = np.nonzero(out_a > 10)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    path = os.path.join(OUT, "Futarino1_T4_約束线稿.png")
    save_rgba(path, out_rgb[box[1]:box[3], box[0]:box[2]], out_a[box[1]:box[3], box[0]:box[2]])
    return path, dict(task="T20261027_005825", size=(box[2] - box[0], box[3] - box[1]))


# ---------------- 任务 4：床 + 右侧（沿床沿斜线裁） ----------------
def task4():
    bgr = imread(os.path.join(TASKS, "T20261027_005758.png"))
    rgb, H, S, V, R, G, B = hsv_parts(bgr)
    h, w = bgr.shape[:2]

    # 床沿斜线：顶部 (480,80) 到 底部 (280,800)，保留右侧
    top = (480.0, 78.0)
    bot = (280.0, 802.0)
    yy, xx = np.mgrid[0:h, 0:w]
    t = (yy - top[1]) / (bot[1] - top[1])
    cut_x = top[0] + (bot[0] - top[0]) * t
    keep = (xx >= cut_x) & (yy >= 72) & (yy <= 803) & (xx <= 1824)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # 线稿图：背景是均匀蓝，线条明显更暗，用自适应阈值
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 15, 9)
    ink = (ink > 0) & keep
    ink = ndimage.binary_opening(ink, np.ones((2, 2)))

    line = ink.astype(np.float32)
    out_rgb = np.zeros_like(bgr)
    out_a = (np.clip(line, 0, 1) * 255).astype(np.uint8)
    ys, xs = np.nonzero(out_a > 10)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    path = os.path.join(OUT, "Futarino1_T3_床线稿.png")
    save_rgba(path, out_rgb[box[1]:box[3], box[0]:box[2]], out_a[box[1]:box[3], box[0]:box[2]])
    return path, dict(task="T20261027_005758", size=(box[2] - box[0], box[3] - box[1]))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    argv = sys.argv[1:]
    detail, width = 0.0, 3
    which = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--detail":
            detail = float(argv[i + 1]); i += 2
        elif a == "--width":
            width = int(argv[i + 1]); i += 2
        else:
            which.append(a); i += 1
    if not which:
        which = ["all"]
    res = []
    if "T1" in which or "all" in which:
        res.append(task1(detail, width))
    if "T2" in which or "all" in which:
        res.append(task2())
    if "T3" in which or "all" in which:
        res.append(task3())
    if "T4" in which or "all" in which:
        res.append(task4())
    for p, meta in res:
        print(meta, "->", os.path.basename(p))
