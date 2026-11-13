# 2026-10-29 20:20:00 G21 基线：反相法（白底黑线）与 MangaLine 并行，判断每张走哪条
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g21")

from extract_f2 import save_rgba  # noqa: E402
from extract_f3 import mle_line  # noqa: E402

IDS = ["T20261029_195142", "T20261029_195153", "T20261029_195202",
       "T20261029_195219", "T20261029_195238", "T20261029_195249",
       "T20261029_195258", "T20261029_195307", "T20261029_195310",
       "T20261029_195328", "T20261029_195431", "T20261029_195450",
       "T20261029_195457", "T20261029_195506", "T20261029_195509",
       "T20261029_195511", "T20261029_195514"]


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def invert(roi, floor=40):
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    a = 255.0 - g
    a[a < floor] = 0
    return a


def stats(tid, roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V = hsv[..., 2].astype(np.float32)
    S = hsv[..., 1].astype(np.float32)
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    print("%s %-10s V[%3.0f %3.0f %3.0f] S[%3.0f %3.0f] gray[%3.0f %3.0f %3.0f]" % (
        tid[-6:], "%dx%d" % (roi.shape[1], roi.shape[0]),
        *[np.percentile(V, q) for q in (10, 50, 90)],
        *[np.percentile(S, q) for q in (10, 90)],
        *[np.percentile(g, q) for q in (10, 50, 90)]))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for tid in IDS:
        roi = roi_of(tid)
        stats(tid, roi)
        save_rgba(os.path.join(OUT, "_inv_" + tid + ".png"), invert(roi), 1.2, soft=True)
        save_rgba(os.path.join(OUT, "_mle_" + tid + ".png"),
                  mle_line(roi, clahe=True) * 255.0, 1.2, soft=True)
