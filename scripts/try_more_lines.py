# 2026-10-28 23:20:00 线条过少的四张：多尺度叠加与低阈值对比
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

from extract_f2 import save_rgba  # noqa: E402
from extract_f3 import mle_line, dark_lines  # noqa: E402

JOBS = [("T20261028_190853", "电台"), ("T20261028_190956", "双人"),
        ("T20261028_191020", "鸽子"), ("T20261028_191030", "鸽子屋顶")]


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def multi_scale(roi, scales=(0.75, 1.0, 1.5), thr=0.008, span=0.35):
    h, w = roi.shape[:2]
    acc = np.zeros((h, w), np.float32)
    for s in scales:
        if s == 1.0:
            sub, (dw, dh) = roi, (w, h)
        else:
            dw, dh = max(32, int(w * s)), max(32, int(h * s))
            sub = cv2.resize(roi, (dw, dh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        l = mle_line(sub, thr=thr, span=span, clahe=True)
        if (dw, dh) != (w, h):
            l = cv2.resize(l, (w, h), interpolation=cv2.INTER_LINEAR)
        acc = np.maximum(acc, l)
    return acc


def low_thr(roi):
    return mle_line(roi, thr=0.006, span=0.30, clahe=True)


def with_dark(roi, base):
    d = dark_lines(roi, sigma=3, t1=1.2, t2=6.0)
    return np.maximum(base, d * 0.55)


if __name__ == "__main__":
    for tid, tag in JOBS:
        roi = roi_of(tid)
        print(tid, tag, roi.shape)
        save_rgba(os.path.join(REV, "_d_%s_ms.png" % tid[-6:]),
                  multi_scale(roi) * 255.0, 1.4, soft=True)
        save_rgba(os.path.join(REV, "_d_%s_low.png" % tid[-6:]),
                  low_thr(roi) * 255.0, 1.4, soft=True)
        save_rgba(os.path.join(REV, "_d_%s_mix.png" % tid[-6:]),
                  with_dark(roi, multi_scale(roi)) * 255.0, 1.4, soft=True)
