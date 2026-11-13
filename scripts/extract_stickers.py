# 2026-10-27 01:30:00 从工作台提交的截图中抠出元素，输出透明底 PNG
# 用法: python scripts/extract_stickers.py T1 | T2 | all
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


def imwrite(path, bgr):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, bgr)
    if not ok:
        raise RuntimeError("encode failed " + path)
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def bgra(path):
    """读成 BGR + 原 alpha。"""
    raw = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if raw.ndim == 3 and raw.shape[2] == 4:
        return raw[:, :, :3].copy(), raw[:, :, 3].copy()
    return raw[:, :, :3].copy(), np.full(raw.shape[:2], 255, np.uint8)


def grow(mask, seed, allowed, iters=3):
    """把 allowed 区域内与 seed 相连的像素并入，重复 iters 次。"""
    cur = seed.copy()
    for _ in range(iters):
        cur = ndimage.binary_dilation(cur, np.ones((3, 3))) & (allowed | cur)
    return cur


def refine(bgr, seed, roi, bg_dist=30, iters=5):
    """用 GrabCut 把粗略掩膜修成贴合边缘的掩膜。"""
    h, w = seed.shape
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    gc[seed] = cv2.GC_PR_FGD
    d = cv2.distanceTransform((~seed).astype(np.uint8), cv2.DIST_L2, 5)
    gc[(d > bg_dist) & roi] = cv2.GC_BGD
    gc[~roi] = cv2.GC_BGD
    bgm = np.zeros((1, 65), np.float64)
    fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc, None, bgm, fgm, iters, cv2.GC_INIT_WITH_MASK)
    return (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)


def color_dist(img, ref):
    a = img.astype(np.float32)
    return np.sqrt(((a - np.array(ref, np.float32)) ** 2).sum(axis=2))


def task1():
    """两个牵手角色 + 脚下草地。"""
    src = os.path.join(TASKS, "T20261027_005710.png")
    bgr, _ = bgra(src)
    h, w = bgr.shape[:2]
    rgb = bgr[:, :, ::-1]
    R, G, B = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    S, V = hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)

    roi = np.zeros((h, w), bool)
    roi[290:804, 700:1235] = True

    # 角色 = 深蓝、高饱和、低明度（排除灰蓝的云影与青色天空）
    core = (S > 130) & (V < 140) & (B > G + 15) & roi
    core = ndimage.binary_closing(core, np.ones((5, 5)))
    lab, n = ndimage.label(core)
    if n:
        sizes = ndimage.sum(core, lab, range(1, n + 1))
        body = lab == (int(np.argmax(sizes)) + 1)
    else:
        body = core
    solid = ndimage.binary_fill_holes(body)
    holes = solid & ~body
    labh, nh = ndimage.label(holes)
    if nh:
        hs = ndimage.sum(holes, labh, range(1, nh + 1))
        body |= np.isin(labh, [i + 1 for i in range(nh) if hs[i] < 800])

    body = refine(bgr, body, roi)
    lab, n = ndimage.label(body)
    if n:
        sizes = ndimage.sum(body, lab, range(1, n + 1))
        body = lab == (int(np.argmax(sizes)) + 1)
    body = ndimage.binary_closing(body, np.ones((5, 5)))
    solid = ndimage.binary_fill_holes(body)
    holes = solid & ~body
    labh, nh = ndimage.label(holes)
    if nh:
        hs = ndimage.sum(holes, labh, range(1, nh + 1))
        body |= np.isin(labh, [i + 1 for i in range(nh) if hs[i] < 600])

    # 剔除 GrabCut 误收的大片云；成片才剔，白袜/高光这类小块保留
    cloud = ((S < 125) & (V > 155)) | ((V > 240) & (S < 45))
    cloud = ndimage.binary_closing(cloud, np.ones((3, 3)))
    labc, nc = ndimage.label(cloud)
    if nc:
        cs = ndimage.sum(cloud, labc, range(1, nc + 1))
        big = [i + 1 for i in range(nc) if cs[i] > 800]
        body &= ~np.isin(labc, big)
    body = ndimage.binary_closing(body, np.ones((3, 3)))

    ys, xs = np.nonzero(body)
    x0, x1 = xs.min(), xs.max()

    # 脚下草坡：角色 x 范围内、脚底高度附近的一小片亮绿
    grass = (G > 140) & (R > 90) & ((G - B) > 50)
    yy = np.arange(h)[:, None]
    xx = np.arange(w)[None, :]
    gmask = grass & (yy >= 748) & (yy <= 792) & (xx >= x0 - 8) & (xx <= x1 + 8)
    gmask = ndimage.binary_closing(gmask, np.ones((1, 41)))
    gmask = ndimage.binary_opening(gmask, np.ones((3, 3)))
    labg, ng = ndimage.label(gmask)
    if ng:
        best = max(range(1, ng + 1), key=lambda i: (labg == i).sum())
        gmask = labg == best
        gmask = ndimage.binary_closing(gmask, np.ones((7, 31)))
        gmask &= (yy >= 746) & (yy <= 793) & (xx >= x0 - 8) & (xx <= x1 + 8)

    fg = body | gmask
    # 去孤立小点
    lab2, n2 = ndimage.label(fg)
    if n2:
        sizes2 = ndimage.sum(fg, lab2, range(1, n2 + 1))
        fg = np.isin(lab2, [i + 1 for i in range(n2) if sizes2[i] > 400])

    alpha = (fg * 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0.7)
    ys, xs = np.nonzero(alpha > 8)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    rgba = np.dstack([rgb.astype(np.uint8), alpha])[box[1]:box[3], box[0]:box[2]]
    out = os.path.join(OUT, "Futarino1_T1_角色牵手草地.png")
    Image.fromarray(rgba, "RGBA").save(out)
    return out, dict(task="T20261027_005710", src_box=box, size=rgba.shape[1::-1])


def task2():
    """俯视鲸鱼剪影。"""
    src = os.path.join(TASKS, "T20261027_005724.png")
    bgr, _ = bgra(src)
    rgb = bgr[:, :, ::-1]
    h, w = bgr.shape[:2]
    R, G, B = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)

    ys0, ys1 = 560, 800
    xs0, xs1 = 790, 1180
    roi = np.zeros((h, w), bool)
    roi[ys0:ys1, xs0:xs1] = True

    # 鲸鱼比周围的青绿背景明显更暗，且偏蓝
    dark = (G < 150) & (B > 90) & (B >= G + 15) & (R < 90)
    dark &= roi
    dark = ndimage.binary_closing(dark, np.ones((7, 7)))
    dark = ndimage.binary_opening(dark, np.ones((3, 3)))
    lab, n = ndimage.label(dark)
    if n:
        best = max(range(1, n + 1), key=lambda i: (lab == i).sum())
        fg = lab == best
    else:
        fg = dark
    fg = ndimage.binary_fill_holes(fg)

    alpha = (fg * 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0.7)
    ys, xs = np.nonzero(alpha > 8)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    rgba = np.dstack([rgb.astype(np.uint8), alpha])[box[1]:box[3], box[0]:box[2]]
    out = os.path.join(OUT, "Futarino1_T2_鲸鱼.png")
    Image.fromarray(rgba, "RGBA").save(out)
    return out, dict(task="T20261027_005724", src_box=box, size=rgba.shape[1::-1])


def preview(paths, dst):
    """把透明底贴到棋盘格和白底上，方便验收。"""
    tiles = []
    for p in paths:
        im = Image.open(p).convert("RGBA")
        W, H = im.size
        pad = 30
        cw, ch = W + pad * 2, H + pad * 2
        for style in ("checker", "white"):
            base = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
            if style == "checker":
                px = base.load()
                for y in range(ch):
                    for x in range(cw):
                        if ((x // 12) + (y // 12)) % 2 == 0:
                            px[x, y] = (222, 222, 222, 255)
            base.alpha_composite(im, (pad, pad))
            tiles.append(base.convert("RGB"))
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows), (250, 250, 250))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    sheet.save(dst)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = []
    if which in ("T1", "all"):
        results.append(task1())
    if which in ("T2", "all"):
        results.append(task2())
    for p, meta in results:
        print(meta, "->", os.path.basename(p))
    if results:
        preview([p for p, _ in results], os.path.join(OUT, "_preview.png"))
