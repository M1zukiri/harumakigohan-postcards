# 2026-10-28 23:00:00 路牌用圆牌/立柱/方板三段几何掩膜，只留路牌本体
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers",
                   "G04-G07_コバルトメモリーズ_セブンティーナ")

from extract_f2 import save_rgba  # noqa: E402
from extract_f3 import mle_line  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def measure(roi):
    """用暗描边定位圆牌、方板，打印以便核对几何掩膜坐标。"""
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    dark = (g < 105).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    dark = ndimage.binary_fill_holes(dark > 0).astype(np.uint8)
    lab, n = ndimage.label(dark)
    print("  暗块数", n)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 600:
            continue
        print("   块%d 面积%6d x[%3d,%3d] y[%3d,%3d] 填充%.2f" % (
            i, len(xs), xs.min(), xs.max(), ys.min(), ys.max(), len(xs) / (
                (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1))))


def sign():
    roi = roi_of("T20261028_191111")
    h, w = roi.shape[:2]
    print("路牌原图", w, h)
    measure(roi)
    line = mle_line(roi, clahe=True) * 255.0
    save_rgba(os.path.join(REV, "_sg_line.png"), line, 1.0, soft=True)


if __name__ == "__main__":
    sign()
