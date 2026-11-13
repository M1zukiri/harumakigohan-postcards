# 2026/10/28 03:05:00 线稿/字迹提取技术对比：现有黑帽法 vs Sauvola/Niblack 局部阈值
import os
import sys

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from skimage.filters import threshold_sauvola, threshold_niblack

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_f3 import load_any, trim_bottom, edge_blackhat

REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f3")
os.makedirs(REVIEW, exist_ok=True)


def sauvola_ink(roi, win=31, k=0.10, dark_ink=True):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    t = threshold_sauvola(gray, window_size=win, k=k)
    m = (gray < t) if dark_ink else (gray > t)
    return (m.astype(np.float32))


def niblack_ink(roi, win=31, k=-0.2, dark_ink=True):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    t = threshold_niblack(gray, window_size=win, k=k)
    m = (gray < t) if dark_ink else (gray > t)
    return (m.astype(np.float32))


def preview(items, dst, cols=4, tile=(320, 260)):
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
    """alpha -> 白底黑图，便于观察"""
    a = np.clip(ink * 255, 0, 255).astype(np.uint8)
    rgb = np.zeros((a.shape[0], a.shape[1], 3), np.uint8)
    img = np.dstack([rgb, a])
    im = Image.fromarray(img, "RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, (0, 0), im)
    return bg


def compare(tid, tb=True, win=31, k=0.10):
    j, roi, box = load_any(tid)
    if tb:
        roi = trim_bottom(roi)
    items = []
    items.append((Image.fromarray(roi[:, :, ::-1]).convert("RGB"), "原图"))
    items.append((to_view(edge_blackhat(roi, k=17, thr=9, span=26)), "黑帽 k=17"))
    items.append((to_view(sauvola_ink(roi, win, k)), "Sauvola w%d k%.2f" % (win, k)))
    items.append((to_view(niblack_ink(roi, win, -0.2)), "Niblack w%d" % win))
    items.append((to_view(sauvola_ink(roi, win * 2 + 1, k)), "Sauvola w%d" % (win * 2 + 1)))
    items.append((to_view(niblack_ink(roi, win * 2 + 1, -0.25)), "Niblack w%d" % (win * 2 + 1)))
    dst = os.path.join(REVIEW, "_tech_%s.png" % tid[-6:])
    print(tid, preview(items, dst))
    return dst


if __name__ == "__main__":
    compare("T20261027_232448", tb=False, win=25, k=0.10)
    compare("T20261027_232329", tb=True, win=25, k=0.10)
