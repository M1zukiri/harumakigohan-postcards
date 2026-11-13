# 2026-10-28 21:50:00 按蒙版保留区提取线稿，轮廓实线、内部线条限制在蒙版内
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

# name, 组, 内部线条来源（A=全图 MangaLine，D=再叠局部 dark_lines）
JOBS = {
    "M20261027_223312": ("F2_人物_低头与天线.png", "Futarino2", "A"),
    "M20261027_223914": ("F1_人物_王冠与长裙.png", "Futarino1", "D"),
    "M20261027_223955": ("F1_人物_低头轮廓.png", "Futarino1", "A"),
}


def load(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    src = np.array(Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB"))
    msk = np.array(Image.open(os.path.join(TASKS, j["mask_file"])).convert("RGBA"))
    return j, cv2.cvtColor(src, cv2.COLOR_RGB2BGR), msk[..., 3]


def build(tid, mode):
    j, roi, alpha = load(tid)
    mb = ndimage.binary_fill_holes(
        ndimage.binary_closing(alpha > 24, np.ones((9, 9))))
    soft = np.clip(cv2.GaussianBlur(mb.astype(np.float32), (0, 0), 4) * 2.2, 0, 1)
    edge = contour_alpha(mb, 2.8, ss=4)

    line = mle_line(roi, clahe=True) * 255.0
    a = np.clip(np.maximum(line * soft, edge), 0, 255)
    if mode == "D":
        ys, xs = np.nonzero(alpha > 24)
        x0, y0 = max(0, xs.min() - 12), max(0, ys.min() - 12)
        x1, y1 = min(roi.shape[1], xs.max() + 13), min(roi.shape[0], ys.max() + 13)
        sub = roi[y0:y1, x0:x1]
        big = cv2.resize(sub, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        d = dark_lines(big, sigma=3, t1=1.5, t2=8.0)
        d = cv2.resize(d, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
        full = np.zeros(roi.shape[:2], np.float32)
        full[y0:y1, x0:x1] = d
        a = np.clip(np.maximum(a, full * 255.0 * soft), 0, 255)
    return a


def main(only=None):
    for tid, (name, group, mode) in JOBS.items():
        if only and tid not in only:
            continue
        a = build(tid, mode)
        save_rgba(os.path.join(OUT, "_mk2_" + tid + ".png"), a, 1.4, soft=True)
        dst = os.path.join(ROOT, "postcards", "_workbench", "stickers", group, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        w, h = save_rgba(dst, a, 1.4, soft=True)
        print("%s -> %s/%s  %dx%d" % (tid, group, name, w, h))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
