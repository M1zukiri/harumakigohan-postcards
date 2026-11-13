# 2026/10/28 04:50:00 饭团重做：线稿模型给出真实轮廓点，径向函数只在有线条的角度取值，缺角插值补全
import os
import sys

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from mle import manga_lines
from extract_f2 import save_rgba

TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers_f2")
REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f3")
MID = "M20261027_223312"


def load_parts(pad=40):
    img = np.array(Image.open(os.path.join(TASKS, MID + ".png")).convert("RGB"))
    mk = np.array(Image.open(os.path.join(TASKS, MID + "_mask.png")).convert("RGBA"))
    painted = mk[..., 3] > 40
    keep = painted & (mk[..., 1] > 130) & (mk[..., 0] < 130)
    keep = ndimage.binary_closing(keep, np.ones((11, 11)))
    keep = ndimage.binary_fill_holes(keep)
    lab, n = ndimage.label(keep)
    if n:
        sizes = ndimage.sum(keep, lab, range(1, n + 1))
        keep = lab == (int(np.argmax(sizes)) + 1)
    ys, xs = np.nonzero(keep)
    x0, x1 = max(0, xs.min() - pad), min(img.shape[1], xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(img.shape[0], ys.max() + pad)
    return img[y0:y1, x0:x1], keep[y0:y1, x0:x1], (x0, y0, x1, y1)


def radial_from_lines(line_bin, center, n_ang=720, max_r=None):
    """对每个角度沿射线找最远的线稿像素；没有线条的角度记 NaN。"""
    h, w = line_bin.shape
    cy, cx = center
    if max_r is None:
        max_r = int(np.hypot(h, w))
    angs = np.linspace(-np.pi, np.pi, n_ang, endpoint=False)
    r = np.full(n_ang, np.nan, np.float32)
    steps = np.arange(0, max_r, 1.0)
    for i, a in enumerate(angs):
        ys = np.round(cy + steps * np.sin(a)).astype(int)
        xs = np.round(cx + steps * np.cos(a)).astype(int)
        ok = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w)
        if not ok.any():
            continue
        ys, xs = ys[ok], xs[ok]
        hit = np.nonzero(line_bin[ys, xs])[0]
        if len(hit):
            r[i] = steps[ok][hit[-1]]
    return angs, r


def fill_gaps(angs, r, smooth_n=9):
    """把缺角度（被遮挡）按相邻已知值线性插值补上，再整体平滑。"""
    good = ~np.isnan(r)
    if good.sum() < 8:
        return None
    rr = r.copy()
    idx = np.arange(len(rr))
    rr[~good] = np.interp(idx[~good], idx[good], rr[good], period=len(rr))
    if smooth_n > 1:
        rr = ndimage.uniform_filter1d(rr, smooth_n, mode="wrap")
    return rr


def build_contour(angs, rr, center):
    cy, cx = center
    pts = np.stack([cx + rr * np.cos(angs), cy + rr * np.sin(angs)], axis=1)
    return pts


def draw_closed(shape, pts, width=3, ss=4):
    h, w = shape
    canvas = np.zeros((h * ss, w * ss), np.uint8)
    p = np.round(pts * ss).astype(np.int32)
    cv2.polylines(canvas, [p], True, 255, max(1, width * ss), cv2.LINE_AA)
    return cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)


def preview(items, dst, cols=3, tile=(400, 360)):
    f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    tiles = []
    for im, label in items:
        W, H = im.size
        k = min((tile[0] - 12) / W, (tile[1] - 34) / H)
        im2 = im.resize((max(1, int(W * k)), max(1, int(H * k))), Image.LANCZOS)
        c = Image.new("RGB", tile, (255, 255, 255))
        c.paste(im2, (6, 24))
        ImageDraw.Draw(c).text((6, 4), label, fill=(30, 30, 30), font=f)
        tiles.append(c)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tile[0] * cols, tile[1] * rows), (235, 235, 238))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tile[0], (i // cols) * tile[1]))
    sheet.save(dst)
    return sheet.size


def to_view(ink):
    a = np.clip(ink * 255, 0, 255).astype(np.uint8)
    rgb = np.zeros((a.shape[0], a.shape[1], 3), np.uint8)
    im = Image.fromarray(np.dstack([rgb, a]), "RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, (0, 0), im)
    return bg


def main():
    roi, keep, box = load_parts()
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    ml = manga_lines(gray)
    ml_ink = 1.0 - ml / 255.0
    lines = (ml_ink > 0.35).astype(np.uint8)
    lines = ndimage.binary_closing(lines, np.ones((3, 3)))
    region = ndimage.binary_dilation(keep, np.ones((25, 25)))
    lines_in = lines & region

    ys, xs = np.nonzero(keep)
    cy, cx = float(ys.mean()), float(xs.mean())

    # 方案 A：以蒙版自身边界做径向，三种平滑强度
    angs_m, r_m = radial_from_lines(keep, (cy, cx), 720)
    variants = []
    for mf, gf in [(45, 10), (25, 6), (15, 4)]:
        rr = fill_gaps(angs_m, r_m, smooth_n=1)
        if rr is None:
            continue
        rr = ndimage.maximum_filter1d(rr, mf, mode="wrap")
        rr = ndimage.gaussian_filter1d(rr, gf, mode="wrap")
        pts = build_contour(angs_m, rr, (cy, cx))
        variants.append((draw_closed(gray.shape, pts, 3), "蒙版径向 mf%d gf%d" % (mf, gf)))

    # 方案 B：真实线稿点做径向
    angs, r = radial_from_lines(lines_in, (cy, cx), 720)
    rr2 = fill_gaps(angs, r, smooth_n=11)
    pts2 = build_contour(angs, rr2, (cy, cx))
    line_outline = draw_closed(gray.shape, pts2, 3)

    # 海苔：只取饭团内部最暗且面积最大的块
    g = gray.astype(np.float32)
    inner = ndimage.binary_erosion(keep, np.ones((9, 9)))
    nori = (g < 45) & inner
    nori = ndimage.binary_opening(nori, np.ones((9, 9)))
    nori = ndimage.binary_closing(nori, np.ones((21, 21)))
    lab, n = ndimage.label(nori)
    if n:
        sizes = ndimage.sum(nori, lab, range(1, n + 1))
        nori = lab == (int(np.argmax(sizes)) + 1)
    nori = ndimage.binary_fill_holes(nori)
    print("海苔面积 %d，占比 %.1f%%" % (int(nori.sum()), 100.0 * nori.sum() / keep.sum()))

    items = [(Image.fromarray(roi).convert("RGB"), "原图 ROI"), (to_view(ml_ink), "线稿模型")]
    items += [(to_view(v / 255.0), lab_) for v, lab_ in variants]
    items.append((to_view(np.clip(line_outline / 255.0 + lines_in * 0.55, 0, 1)), "线稿点径向"))
    cur = Image.open(os.path.join(ROOT, "postcards", "_workbench", "stickers", "Futarino2", "F2_饭团.png")).convert("RGBA")
    bg = Image.new("RGB", cur.size, (255, 255, 255))
    bg.paste(cur, (0, 0), cur)
    items.append((bg, "现有 F2_饭团"))
    print(preview(items, os.path.join(REVIEW, "_onigiri_radial.png")))

    # 输出优选方案：mf25/gf6 + 新海苔
    best = variants[1][0] if len(variants) > 1 else variants[0][0]
    combined = np.clip(best / 255.0 + nori.astype(np.float32), 0, 1)
    p = os.path.join(OUT, "F2_饭团_试验.png")
    w, h = save_rgba(p, combined * 255, 1.5)
    print("试验输出", p, (w, h))


if __name__ == "__main__":
    main()
