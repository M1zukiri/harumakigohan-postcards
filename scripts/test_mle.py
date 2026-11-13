# 2026/10/28 03:25:00 三种线稿方案对比：形态学黑帽 / Sauvola 局部阈值 / MangaLineExtraction 深度模型
import os
import sys
import time

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from skimage.filters import threshold_sauvola

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_f3 import load_any, trim_bottom, edge_blackhat

REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f3")
os.makedirs(REVIEW, exist_ok=True)


def sauvola_ink(roi, win=25, k=0.10):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    t = threshold_sauvola(gray, window_size=win, k=k)
    return (gray < t).astype(np.float32)


def to_view(ink):
    a = np.clip(ink * 255, 0, 255).astype(np.uint8)
    rgb = np.zeros((a.shape[0], a.shape[1], 3), np.uint8)
    im = Image.fromarray(np.dstack([rgb, a]), "RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, (0, 0), im)
    return bg


def preview(items, dst, cols=4, tile=(340, 280)):
    f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    tiles = []
    for im, label in items:
        W, H = im.size
        kk = min((tile[0] - 12) / W, (tile[1] - 34) / H)
        im2 = im.resize((max(1, int(W * kk)), max(1, int(H * kk))), Image.LANCZOS)
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


def run(tid, tb=False, mle_side=1400):
    from mle import manga_lines
    j, roi, box = load_any(tid)
    if tb:
        roi = trim_bottom(roi)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    t0 = time.time()
    ml = manga_lines(gray, max_side=mle_side)
    dt = time.time() - t0
    items = [
        (Image.fromarray(roi[:, :, ::-1]).convert("RGB"), "原图"),
        (to_view(edge_blackhat(roi, k=17, thr=9, span=26)), "黑帽 k=17"),
        (to_view(sauvola_ink(roi, 25, 0.10)), "Sauvola w25"),
        (to_view(1.0 - ml / 255.0), "MangaLine (%.2fs)" % dt),
        (to_view(np.clip((0.62 - ml / 255.0) / 0.50, 0, 1)), "MangaLine thr"),
        (to_view(np.clip((0.75 - ml / 255.0) / 0.55, 0, 1)), "MangaLine thr+"),
    ]
    dst = os.path.join(REVIEW, "_mle_%s.png" % tid[-6:])
    print(tid, "mle %.2fs" % dt, "max=%.0f mean=%.1f" % (ml.max(), ml.mean()), preview(items, dst))
    return dst


if __name__ == "__main__":
    for tid, tb in [("T20261027_232329", True), ("T20261027_232423", False),
                    ("T20261027_232520", True), ("T20261027_232448", False)]:
        run(tid, tb)
