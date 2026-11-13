# 2026-10-28 20:00:00 对 4 张失败图试多种线稿方案，横向比对
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

from extract_f2 import save_rgba, contour_alpha  # noqa: E402
from extract_f3 import mle_line, dark_lines, bright_lines, norm_stroke  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def lab_mask(roi, dark=True, thr=None):
    """按 Lab 亮度分割暗/亮主体。"""
    L = cv2.cvtColor(roi, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32) * 100 / 255
    if thr is None:
        thr = np.percentile(L, 35) if dark else np.percentile(L, 80)
    m = (L < thr) if dark else (L > thr)
    m = ndimage.binary_opening(m, np.ones((3, 3)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.zeros_like(m)
        for i in range(1, n + 1):
            if sizes[i - 1] >= 0.008 * m.size:
                keep |= lab == i
        m = keep
    return m


def edge_sobel(roi, t=18):
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    e = np.hypot(gx, gy)
    e = e / max(e.max(), 1e-6) * 255
    e = np.clip((e - t) * 255.0 / max(255 - t, 1), 0, 255)
    return e


def out(tid, tag, a):
    p = os.path.join(REV, "_x_" + tid[-6:] + "_" + tag + ".png")
    save_rgba(p, a, 1.4, soft=True)
    return p


def t_190853():
    roi = roi_of("T20261028_190853")
    print("190853 shape", roi.shape)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V = hsv[..., 2].astype(np.float32)
    L = cv2.cvtColor(roi, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32) * 100 / 255
    print("  V pct", [round(float(np.percentile(V, q))) for q in (5, 25, 50, 75, 95)])
    print("  L pct", [round(float(np.percentile(L, q))) for q in (5, 25, 40, 50, 75, 95)])
    m = lab_mask(roi, dark=True, thr=float(np.percentile(L, 40)))
    print("  mask frac", round(float(m.mean()), 4))
    out("T20261028_190853", "mle_clahe", mle_line(roi, clahe=True) * 255)
    c = contour_alpha(m, 3, ss=4)
    print("  contour max", float(c.max()))
    out("T20261028_190853", "contour", c)
    inner = edge_sobel(roi, 12) * np.clip(m.astype(np.float32) * 1.4, 0, 1) * 0.85
    out("T20261028_190853", "contour_inner", np.clip(np.maximum(c, inner), 0, 255))


def t_191149():
    roi = roi_of("T20261028_191149")
    V = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32)
    print("191149 V pct", [round(float(np.percentile(V, q))) for q in (5, 50, 90, 97, 99.5)])
    out("T20261028_191149", "mle_inv", mle_line(255 - roi, clahe=False) * 255)
    out("T20261028_191149", "mle_inv_clahe", mle_line(255 - roi, clahe=True) * 255)
    out("T20261028_191149", "bright110", bright_lines(roi, 110) * 255)
    out("T20261028_191149", "bright140", bright_lines(roi, 140) * 255)


def t_191238():
    roi = roi_of("T20261028_191238")
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    print("191238 H pct", [round(float(np.percentile(H, q))) for q in (5, 25, 50, 75, 95)])
    pink = (H > 150) & (H < 179) & (S > 60) & (V > 120)
    pink = ndimage.binary_closing(pink, np.ones((5, 5)))
    pink = ndimage.binary_fill_holes(pink)
    print("  pink frac", round(float(pink.mean()), 4))
    out("T20261028_191238", "pink_contour", contour_alpha(pink, 3, ss=4))
    out("T20261028_191238", "sobel", edge_sobel(roi, 10) * 255)


def t_190938():
    roi = roi_of("T20261028_190938")
    out("T20261028_190938", "dark", dark_lines(roi, sigma=4, t1=2.0, t2=9.0) * 255)
    out("T20261028_190938", "mle_clahe", mle_line(roi, clahe=True) * 255)
    out("T20261028_190938", "sobel", edge_sobel(roi, 14) * 255)


if __name__ == "__main__":
    t_190853()
    t_191149()
    t_191238()
    t_190938()
