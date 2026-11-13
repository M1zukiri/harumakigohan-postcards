# 2026-10-29 01:20:00 223706 改为灰度贴纸：粉色映射为浅灰，保留人物明暗层次
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g13")


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def gray_variant(roi, white=190, gamma=0.85, contrast=1.0):
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    g = np.power(g, gamma)
    g = np.clip((g - 0.5) * contrast + 0.5, 0, 1)
    g = g * (white / 255.0)
    return np.clip(g * 255, 0, 255).astype(np.uint8)


def save_gray(path, gray):
    rgb = np.dstack([gray, gray, gray])
    a = np.full(gray.shape, 255, np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)


if __name__ == "__main__":
    roi = roi_of("T20261028_223706")
    print("orig", roi.shape)
    for white, gamma, con in [(190, 0.85, 1.0), (170, 0.9, 1.15), (210, 0.8, 1.0)]:
        g = gray_variant(roi, white, gamma, con)
        p = os.path.join(REV, "_gray_%d_%.2f_%.2f.png" % (white, gamma, con))
        save_gray(p, g)
        print(p, "p5=%.0f p50=%.0f p95=%.0f" % tuple(
            np.percentile(g, [5, 50, 95])))
