# 2026-10-28 20:45:00 调试粉色前景与演出票的提取参数
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
from extract_f3 import mle_line, dark_lines  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def pink_mask(roi, hmin=150, hmax=179, s_min=60, v_min=120):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S, V = [hsv[..., i].astype(np.int16) for i in range(3)]
    m = (H > hmin) & (H < hmax) & (S > s_min) & (V > v_min)
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    return ndimage.binary_fill_holes(m)


def scene_variants():
    roi = roi_of("T20261028_191238")
    print("191238", roi.shape)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S, V = [hsv[..., i].astype(np.int16) for i in range(3)]
    print("  H pct", [round(float(np.percentile(H, q))) for q in (5, 50, 95)])
    print("  S pct", [round(float(np.percentile(S, q))) for q in (5, 50, 95)])
    print("  V pct", [round(float(np.percentile(V, q))) for q in (5, 50, 95)])

    for tag, kw in [("p60", dict(hmin=145, hmax=179, s_min=50, v_min=100)),
                    ("p40", dict(hmin=140, hmax=179, s_min=40, v_min=90))]:
        m = pink_mask(roi, **kw)
        print(" ", tag, "frac", round(float(m.mean()), 3))
        for wd, t in [(2.2, "a"), (4.0, "b")]:
            a = contour_alpha(m, wd, ss=4)
            p = os.path.join(REV, "_sc_%s_%s.png" % (tag, t))
            save_rgba(p, a, 1.3, soft=True)

    m = pink_mask(roi, hmin=150)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m = lab == (int(np.argmax(sizes)) + 1)
    a = contour_alpha(m, 4.0, ss=4)
    p = os.path.join(REV, "_sc_main_b.png")
    save_rgba(p, a, 1.3, soft=True)

    dark = (V < 105)
    dark = ndimage.binary_closing(dark, np.ones((5, 5)))
    dark = ndimage.binary_opening(dark, np.ones((3, 3)))
    print("  dark frac", round(float(dark.mean()), 4))
    dd = contour_alpha(dark, 2.5, ss=4)
    p = os.path.join(REV, "_sc_dark.png")
    save_rgba(p, np.clip(np.maximum(a, dd), 0, 255), 1.3, soft=True)


def ticket_variants():
    roi = roi_of("T20261028_191133")
    line = mle_line(roi, clahe=True) * 255.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16)
    cy = ndimage.binary_closing((H > 80) & (H < 112) & (S > 60), np.ones((5, 5)))
    print("191133 cyan frac", round(float(cy.mean()), 3))
    for pad in (34, 60, 90):
        m = cv2.dilate(cy.astype(np.uint8), np.ones((pad, pad), np.uint8))
        g = cv2.GaussianBlur(m.astype(np.float32), (0, 0), pad / 4.0)
        g = np.clip(g * 2.0, 0, 1)
        p = os.path.join(REV, "_tk_pad%d.png" % pad)
        save_rgba(p, line * g, 1.5, soft=True)


if __name__ == "__main__":
    scene_variants()
    ticket_variants()
