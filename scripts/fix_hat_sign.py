# 2026-10-28 22:45:00 草帽限暖色相、路牌限最大灰色连通域，去人物与灌木路面
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
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers",
                   "G04-G07_コバルトメモリーズ_セブンティーナ")

from extract_f2 import save_rgba, keep_components  # noqa: E402
from extract_f3 import mle_line  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def soften(m, blur=6, gain=1.8):
    m = ndimage.binary_fill_holes(m.astype(bool))
    g = cv2.GaussianBlur(m.astype(np.float32), (0, 0), blur)
    return np.clip(g * gain, 0, 1)


def hat():
    roi = roi_of("T20261028_190908")
    H = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[..., 0].astype(np.int16)
    warm = cv2.morphologyEx((H < 65).astype(np.uint8), cv2.MORPH_CLOSE,
                            np.ones((15, 15), np.uint8))
    a = mle_line(roi, clahe=True) * 255.0 * soften(warm)
    w, h = save_rgba(os.path.join(DST, "G04_草帽.png"), a, 1.8, soft=True)
    print("草帽", w, h)


def sign():
    roi = roi_of("T20261028_191111")
    h, w = roi.shape[:2]
    # 路牌由圆牌 + 立柱 + 方板三段构成，用几何掩膜把路面与灌木挡在外面
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (97, 110), (53, 79), 0, 0, 360, 1, -1)
    cv2.rectangle(m, (86, 172), (114, h - 1), 1, -1)
    cv2.rectangle(m, (56, 196), (133, 398), 1, -1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    a = mle_line(roi, clahe=True) * 255.0 * soften(m, 3, 2.4)
    a[m == 0] = 0
    # 方板以下只留立柱，清掉左右两侧的路面横线与草丛
    a[398:, :] = 0
    a[196:, :56] = 0
    a[196:, 133:] = 0
    w2, h2 = save_rgba(os.path.join(DST, "G04_路牌.png"), a, 1.6, soft=True)
    print("路牌", w2, h2)


if __name__ == "__main__":
    hat()
    sign()
