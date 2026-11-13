# 2026-10-28 21:40:00 蒙版任务试局部放大与多路合成
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
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")

from extract_f2 import save_rgba, contour_alpha  # noqa: E402
from extract_f3 import mle_line, dark_lines  # noqa: E402

JOBS = ["M20261027_223312", "M20261027_223914", "M20261027_223955"]


def load(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    src = np.array(Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB"))
    msk = np.array(Image.open(os.path.join(TASKS, j["mask_file"])).convert("RGBA"))
    return j, cv2.cvtColor(src, cv2.COLOR_RGB2BGR), msk[..., 3]


def bbox_of(m, pad=12):
    ys, xs = np.nonzero(m > 24)
    if not len(xs):
        return None
    return (max(0, xs.min() - pad), max(0, ys.min() - pad),
            min(m.shape[1], xs.max() + pad + 1), min(m.shape[0], ys.max() + pad + 1))


def clahe_gray(roi, clip=3.0, tile=6):
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(g)


def local_line(roi, box, zoom=2.0, clahe=True):
    """在 bbox 内裁一块放大后跑 MangaLine，返回全图大小的 alpha。"""
    x0, y0, x1, y1 = box
    sub = roi[y0:y1, x0:x1]
    if zoom != 1.0:
        sub = cv2.resize(sub, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    l = mle_line(sub, clahe=clahe)
    if zoom != 1.0:
        l = cv2.resize(l, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    out = np.zeros(roi.shape[:2], np.float32)
    out[y0:y1, x0:x1] = l
    return out


def variants(tid):
    j, roi, alpha = load(tid)
    mb = alpha > 24
    mb = ndimage.binary_closing(mb, np.ones((9, 9)))
    mb = ndimage.binary_fill_holes(mb)
    box = bbox_of(alpha)
    print(tid, "box", box, "mask px", int(mb.sum()))
    soft = np.clip(cv2.GaussianBlur(mb.astype(np.float32), (0, 0), 4) * 2.2, 0, 1)

    edge = contour_alpha(mb, 2.8, ss=4)

    # A：全图 MangaLine 限制在蒙版内
    a1 = mle_line(roi, clahe=True) * 255.0
    v1 = np.clip(np.maximum(a1 * soft, edge), 0, 255)
    save_rgba(os.path.join(OUT, "_mv_%s_A.png" % tid[-6:]), v1, 1.4, soft=True)

    # B：bbox 放大 2 倍后 MangaLine
    v2 = np.clip(np.maximum(local_line(roi, box, 2.0) * 255.0 * soft, edge), 0, 255)
    save_rgba(os.path.join(OUT, "_mv_%s_B.png" % tid[-6:]), v2, 1.4, soft=True)

    # C：bbox 放大 + 灰度 CLAHE 后 dark_lines
    x0, y0, x1, y1 = box
    sub = roi[y0:y1, x0:x1]
    sub2 = cv2.resize(sub, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    d = dark_lines(sub2, sigma=3, t1=1.5, t2=8.0)
    d = cv2.resize(d, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    full = np.zeros(roi.shape[:2], np.float32)
    full[y0:y1, x0:x1] = d
    v3 = np.clip(np.maximum(full * 255.0 * soft, edge), 0, 255)
    save_rgba(os.path.join(OUT, "_mv_%s_C.png" % tid[-6:]), v3, 1.4, soft=True)

    # D：A 与 C 取并集
    v4 = np.clip(np.maximum(v1, v3), 0, 255)
    save_rgba(os.path.join(OUT, "_mv_%s_D.png" % tid[-6:]), v4, 1.4, soft=True)


if __name__ == "__main__":
    for t in JOBS:
        variants(t)
