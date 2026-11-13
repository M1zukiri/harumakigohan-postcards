# 2026/10/28 04:35:00 饭团重做：线稿模型提轮廓 + 主动轮廓（snake）补全被手遮挡的边界
import os
import sys

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from skimage.filters import gaussian
from skimage.segmentation import active_contour

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from mle import manga_lines
from extract_f2 import contour_alpha, save_rgba

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


def snake_outline(mask_img, ml_ink, n_pts=600, alpha=0.020, beta=12.0, gamma=0.002, iters=2500):
    """以饭团可见区域拟合的椭圆为初值，在线稿强度图上演化出完整闭合轮廓。"""
    ys, xs = np.nonzero(mask_img)
    cy, cx = ys.mean(), xs.mean()
    ry = max(6.0, (ys.max() - ys.min()) / 2.0 * 1.16)
    rx = max(6.0, (xs.max() - xs.min()) / 2.0 * 1.16)
    s = np.linspace(0, 2 * np.pi, n_pts)
    init = np.stack([cy + ry * np.sin(s), cx + rx * np.cos(s)], axis=1)
    # snake 在"线稿亮 = 有吸引力"的图上工作
    img = gaussian(ml_ink.astype(np.float32), 2.5)
    img = img / max(img.max(), 1e-6)
    snake = active_contour(img, init, alpha=alpha, beta=beta, gamma=gamma,
                           max_num_iter=iters, convergence=1e-4)
    return snake


def draw_snake(shape, snake, width=3):
    h, w = shape
    big = 4
    canvas = np.zeros((h * big, w * big), np.uint8)
    pts = np.round(snake * big).astype(np.int32)
    cv2.polylines(canvas, [pts], True, 255, max(1, width * big), cv2.LINE_AA)
    return cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)


def preview(items, dst, cols=3, tile=(400, 340)):
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
    # 海苔：原图里最暗的一块
    g = gray.astype(np.float32)
    nori = (g < 60) & keep
    nori = ndimage.binary_opening(nori, np.ones((7, 7)))
    nori = ndimage.binary_closing(nori, np.ones((15, 15)))
    lab, n = ndimage.label(nori)
    if n:
        sizes = ndimage.sum(nori, lab, range(1, n + 1))
        nori = lab == (int(np.argmax(sizes)) + 1)
    nori = ndimage.binary_fill_holes(nori)

    best = None
    for al, be, gm in [(0.020, 12.0, 0.002), (0.010, 20.0, 0.001), (0.035, 8.0, 0.003)]:
        sn = snake_outline(keep, ml_ink, alpha=al, beta=be, gamma=gm)
        outline = draw_snake(gray.shape, sn, 3)
        area = cv2.contourArea(np.round(sn).astype(np.int32))
        target = keep.sum()
        ratio = area / max(target, 1)
        print("snake a=%.3f b=%.0f g=%.3f area=%.0f keep=%d ratio=%.2f" % (al, be, gm, area, target, ratio))
        items = [(to_view(ml_ink), "线稿模型"),
                 (to_view(outline / 255.0), "收敛轮廓 a%.3f b%.0f" % (al, be))]
        if best is None:
            best = sn
    # 第一组作为基准，输出三种参数并列
    rows = []
    for al, be, gm in [(0.020, 12.0, 0.002), (0.010, 20.0, 0.001), (0.035, 8.0, 0.003)]:
        sn = snake_outline(keep, ml_ink, alpha=al, beta=be, gamma=gm)
        rows.append((to_view(draw_snake(gray.shape, sn, 3) / 255.0), "a%.3f b%.0f" % (al, be)))
    items = [(Image.fromarray(roi).convert("RGB"), "原图 ROI"), (to_view(ml_ink), "线稿模型")]
    items += rows
    cur = Image.open(os.path.join(ROOT, "postcards", "_workbench", "stickers", "Futarino2", "F2_饭团.png")).convert("RGBA")
    bg = Image.new("RGB", cur.size, (255, 255, 255))
    bg.paste(cur, (0, 0), cur)
    items.append((bg, "现有 F2_饭团"))
    print(preview(items, os.path.join(REVIEW, "_onigiri_snake.png")))


if __name__ == "__main__":
    main()
