# 2026-10-28 23:55:00 G13 基线：MangaLine 与浅色线检测并行，判断每张图该走哪条路
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g13")

from extract_f2 import save_rgba  # noqa: E402
from extract_f3 import mle_line, bright_lines  # noqa: E402

IDS = ["T20261028_223420", "T20261028_223447", "T20261028_223500",
       "T20261028_223528", "T20261028_223541", "T20261028_223553",
       "T20261028_223602", "T20261028_223636", "T20261028_223706",
       "T20261028_223715", "T20261028_223724"]


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def stats(tid, roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V = hsv[..., 2].astype(np.float32)
    S = hsv[..., 1].astype(np.float32)
    print("%s %-10s V[%3.0f %3.0f %3.0f %3.0f] S[%3.0f %3.0f %3.0f]" % (
        tid[-6:], str(roi.shape[1]) + "x" + str(roi.shape[0]),
        *[np.percentile(V, q) for q in (5, 50, 90, 99)],
        *[np.percentile(S, q) for q in (5, 50, 95)]))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for tid in IDS:
        roi = roi_of(tid)
        stats(tid, roi)
        save_rgba(os.path.join(OUT, "_mle_" + tid + ".png"),
                  mle_line(roi, clahe=True) * 255.0, 1.3, soft=True)
        save_rgba(os.path.join(OUT, "_br_" + tid + ".png"),
                  bright_lines(roi, 130) * 255.0, 1.3, soft=True)
