# 2026-10-29 00:30:00 修 223706 黑白剪影、223636 笔与 223447 右侧脚部
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
GROUP = "G13_第三の心臓"
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", GROUP)
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g13")

from extract_f2 import save_rgba, grabcut_center  # noqa: E402
from extract_f3 import mle_line  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def silhouette_gc(roi, iters=8):
    m = grabcut_center(roi, iters=iters, fg_shrink=0.74, bg_margin=0.02)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V, S = hsv[..., 2].astype(np.int16), hsv[..., 1].astype(np.int16)
    # 深色长袜和鞋子颜色分明，并集补回 GrabCut 漏掉的下半身
    dark = (V < 195) & (S > 60)
    m = m | dark
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.zeros_like(m)
        for i in range(1, n + 1):
            if sizes[i - 1] > 0.0008 * m.size:
                keep |= lab == i
        m = keep
    return m


def pen_only(roi, x0, y0, x1, y1, seed_xy):
    """从笔尖种子出发把笔的笔画连起来，避免把旁边猫脸并进来。"""
    a = mle_line(roi, clahe=True) * 255.0
    b = a > 40
    lab, n = ndimage.label(b, np.ones((3, 3)))
    sx, sy = seed_xy
    if lab[sy, sx] == 0:
        # 种子落在空隙里，就近找一个笔画像素
        ys, xs = np.nonzero(b[y0:y1, x0:x1])
        if not len(xs):
            return a
        sx, sy = xs[0] + x0, ys[0] + y0
    keep = lab == lab[sy, sx]
    for _ in range(10):
        keep = (ndimage.binary_dilation(keep, np.ones((11, 11))) & b) | keep
    m = np.zeros(a.shape, np.float32)
    m[y0:y1, x0:x1] = 1.0
    m = cv2.GaussianBlur(m, (0, 0), 3)
    return a * keep.astype(np.float32) * np.clip(m * 1.6, 0, 1)


if __name__ == "__main__":
    # 223706 剪影
    roi = roi_of("T20261028_223706")
    m = silhouette_gc(roi)
    print("223706 剪影占比", round(float(m.mean()), 3))
    a = np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2), 0, 1) * 255.0
    save_rgba(os.path.join(REV, "_sil_gc.png"), a, 1.4, soft=True)

    # 223636 笔：只取笔身
    roi = roi_of("T20261028_223636")
    a = pen_only(roi, 175, 330, 510, 745, (300, 520))
    save_rgba(os.path.join(REV, "_pen_only.png"), a, 1.8, soft=True)

    # 223447 右侧脚部
    roi = roi_of("T20261028_223447")
    a = mle_line(roi, clahe=True) * 255.0
    a[300:640, 600:] = 0
    save_rgba(os.path.join(REV, "_girl_nofoot.png"), a, 1.4, soft=True)
