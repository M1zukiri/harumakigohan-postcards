# 2026-10-29 20:40:00 G21 ゼロトーキング贴纸提取
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
GROUP = "G21_ゼロトーキング"
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", GROUP)
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g21")

from extract_f2 import save_rgba, contour_alpha  # noqa: E402
from extract_f3 import mle_line  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def gray_of(roi):
    return cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)


def a_line(roi):
    return mle_line(roi, clahe=True) * 255.0


def a_bright(roi):
    """亮笔画压在暗底上：灰度本身就是 alpha。"""
    g = gray_of(roi)
    a = g.copy()
    a[a < 26] = 0
    return a


def a_invert(roi):
    """白底手绘线稿：反相后把弱线拉满，线条一律压到纯黑。"""
    g = gray_of(roi)
    a = 255.0 - g
    a[a < 8] = 0
    if (a > 0).any():
        top = float(np.percentile(a[a > 0], 95))
        a = np.clip(a / max(top, 1.0), 0, 1) ** 0.80 * 255.0
    return a


def a_card(roi):
    """深底上的白卡片：卡片轮廓 + 卡片上的手写字，背景的蓝圈与 STUDI 字不要。"""
    g = gray_of(roi)
    card = (g > 175).astype(np.uint8)
    card = cv2.morphologyEx(card, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    card = ndimage.binary_fill_holes(card > 0).astype(np.uint8)
    lab, n = ndimage.label(card)
    if n:
        sizes = ndimage.sum(card, lab, range(1, n + 1))
        card = (lab == (int(np.argmax(sizes)) + 1)).astype(np.uint8)
    card = cv2.morphologyEx(card, cv2.MORPH_CLOSE, np.ones((19, 19), np.uint8))
    card = ndimage.binary_fill_holes(card > 0).astype(np.uint8)
    edge = contour_alpha(card > 0, 3.0, ss=4)
    inner = np.clip((225.0 - g) * 2.8, 0, 255) * card
    return np.clip(np.maximum(edge, inner), 0, 255)


PLAN = {
    "T20261029_195142": ("G21_四叶草.png", a_line, 1.8),
    "T20261029_195153": ("G21_字迹_ZeloTalking.png", a_bright, 1.5),
    "T20261029_195202": ("G21_花束.png", a_line, 1.6),
    "T20261029_195219": ("G21_拖地的小人.png", a_line, 1.5),
    "T20261029_195238": ("G21_人物_带子.png", a_line, 1.4),
    "T20261029_195249": ("G21_人物_金发.png", a_line, 1.4),
    "T20261029_195258": ("G21_花朵.png", a_line, 2.6),
    "T20261029_195307": ("G21_眼睛_大.png", a_bright, 2.2),
    "T20261029_195310": ("G21_眼睛_小.png", a_bright, 2.6),
    "T20261029_195328": ("G21_卡片与字迹.png", a_card, 1.6),
    "T20261029_195450": ("G21_双人_白裙与蓝衣.png", a_invert, 1.5),
    "T20261029_195457": ("G21_人物_表情.png", a_invert, 1.8),
    "T20261029_195506": ("G21_人物_侧脸.png", a_invert, 1.6),
    "T20261029_195509": ("G21_人物_低头.png", a_invert, 1.7),
    "T20261029_195511": ("G21_人物_纸袋.png", a_invert, 1.6),
    "T20261029_195514": ("G21_人物_跳跃.png", a_invert, 1.7),
}

# 195431 一张图里六组人物，按圆形区块切成六张
SIX = [(40, 55, 400, 435), (388, 55, 730, 435), (718, 55, 1078, 435),
       (40, 455, 400, 835), (348, 455, 692, 835), (695, 455, 1078, 835)]


def main():
    os.makedirs(DST, exist_ok=True)
    for tid, (name, fn, scale) in PLAN.items():
        a = fn(roi_of(tid))
        w, h = save_rgba(os.path.join(DST, name), a, scale, soft=True)
        print("%s %-28s %dx%d" % (tid[-6:], name, w, h))

    roi = roi_of("T20261029_195431")
    line = a_line(roi)
    for i, (x0, y0, x1, y1) in enumerate(SIX, 1):
        m = np.zeros(roi.shape[:2], np.float32)
        m[y0:y1, x0:x1] = 1.0
        m = cv2.GaussianBlur(m, (0, 0), 4)
        name = "G21_六人_%02d.png" % i
        w, h = save_rgba(os.path.join(DST, name), line * np.clip(m * 1.6, 0, 1), 1.6, soft=True)
        print("195431 %-28s %dx%d" % (name, w, h))


if __name__ == "__main__":
    main()
