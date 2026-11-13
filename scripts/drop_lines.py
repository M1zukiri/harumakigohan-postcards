# 2026-10-28 20:35:00 用 Hough 直线检测擦掉画面边框遗留的长直线
import os
import sys
import json

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")

from extract_f2 import save_rgba, contour_alpha  # noqa: E402
from extract_f3 import mle_line, dark_lines, bright_lines  # noqa: E402


def roi_of(tid):
    from PIL import Image
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def drop_long_straight(a, min_ratio=0.5, angle_tol=4.0, erase=6):
    h, w = a.shape
    ref = max(h, w)
    binm = ((a > 35) * 255).astype(np.uint8)
    binm = cv2.dilate(binm, np.ones((3, 3), np.uint8))
    lines = cv2.HoughLinesP(binm, 1, np.pi / 180,
                            threshold=int(ref * 0.30),
                            minLineLength=int(ref * min_ratio),
                            maxLineGap=14)
    n = 0
    if lines is None:
        return a, 0
    for x1, y1, x2, y2 in lines[:, 0]:
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        ang = abs(np.degrees(np.arctan2(dy, dx)))
        if not (ang < angle_tol or ang > 90 - angle_tol):
            continue
        cv2.line(a, (x1, y1), (x2, y2), 0, erase)
        n += 1
    return a, n


PLAN = {
    "T20261028_191004": ("G04_人物_微笑特写.png", lambda r: mle_line(r, clahe=True) * 255.0, 1.2),
    "T20261028_190908": ("G04_草帽.png", lambda r: mle_line(r, clahe=True) * 255.0, 1.8),
    "T20261028_191020": ("G04_鸽子_伏地.png", lambda r: mle_line(r, clahe=True) * 255.0, 1.5),
    "T20261028_191030": ("G04_鸽子_屋顶.png", lambda r: mle_line(r, clahe=True) * 255.0, 1.4),
    "T20261028_190938": ("G04_人物_仰卧特写.png", lambda r: dark_lines(r, sigma=4, t1=2.0, t2=9.0) * 255.0, 1.3),
}

if __name__ == "__main__":
    for tid, (name, fn, scale) in PLAN.items():
        a = fn(roi_of(tid))
        a, n = drop_long_straight(a)
        p = os.path.join(REV, "_ls_" + tid[-6:] + ".png")
        w, h = save_rgba(p, a, scale, soft=True)
        print(tid[-6:], "removed", n, "lines ->", w, h)
