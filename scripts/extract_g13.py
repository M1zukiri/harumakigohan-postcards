# 2026-10-29 00:45:00 G13 第三の心臓贴纸提取：线稿为主，剪影与文字单独处理
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
from extract_f3 import mle_line, bright_lines  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def a_line(roi):
    return mle_line(roi, clahe=True) * 255.0


def a_line_soft(roi):
    """画面本身对比弱时把阈值压下去，宁可多留线。"""
    return mle_line(roi, thr=0.008, span=0.35, clahe=True) * 255.0


def a_text(roi):
    return bright_lines(roi, 110) * 255.0


def a_white_lines(roi):
    """黑底白线插画：直接按亮度取笔画。"""
    return bright_lines(roi, 90) * 255.0


def a_grayscale(roi, white_point=218, gamma=0.90):
    """粉色底还原为纯白，人物面部与服饰的明暗层次按比例提亮后保留。"""
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = np.clip(g / white_point, 0, 1) ** gamma
    return np.clip(g * 255, 0, 255).astype(np.uint8)


def save_gray(path, gray, scale=1.4):
    if scale != 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    rgb = np.dstack([gray, gray, gray])
    a = np.full(gray.shape, 255, np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)
    return gray.shape[1], gray.shape[0]


def a_pen(roi, box, seed):
    """从笔尖种子把笔的笔画连起来，避免把旁边的猫脸并进来。"""
    x0, y0, x1, y1 = box
    a = mle_line(roi, clahe=True) * 255.0
    b = a > 40
    lab, n = ndimage.label(b, np.ones((3, 3)))
    sx, sy = seed
    if lab[sy, sx] == 0:
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


def rect_alpha(shape, box, pad=6):
    x0, y0, x1, y1 = box
    m = np.zeros(shape[:2], np.float32)
    m[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = 1.0
    return cv2.GaussianBlur(m, (0, 0), pad / 2.0)


PLAN = {
    "T20261028_223420": ("G13_书包.png", a_line, 1.5),
    "T20261028_223500": ("G13_双人_背影.png", a_line_soft, 1.4),
    "T20261028_223528": ("G13_心脏.png", a_line, 1.4),
    "T20261028_223541": ("G13_人物_云霄.png", a_line_soft, 1.4),
    "T20261028_223553": ("G13_人物_背影与书包.png", a_line_soft, 1.4),
    "T20261028_223602": ("G13_人物_刘海侧身.png", a_line_soft, 1.4),
    "T20261028_223715": ("G13_字迹_第三の心臓.png", a_text, 1.5),
    "T20261028_223724": ("G13_插画_心形与两人.png", a_white_lines, 1.4),
}


def main():
    os.makedirs(DST, exist_ok=True)

    # 223447 只切右侧另一人的紫鞋，少女自己的腿在 y 620 以下，不能动
    roi = roi_of("T20261028_223447")
    a = a_line(roi)
    a[340:508, 652:] = 0
    a[:340, 700:] = 0
    a[400:460, 630:] = 0
    a[:, 805:] = 0
    w, h = save_rgba(os.path.join(DST, "G13_人物_绿领巾少女.png"), a, 1.4, soft=True)
    print("223447 G13_人物_绿领巾少女.png %dx%d" % (w, h))

    # 223636 四件文具分别取
    roi = roi_of("T20261028_223636")
    line = a_line(roi)
    for box, name, scale in [
        ((380, 0, 684, 560), "G13_铅笔袋.png", 1.6),
        ((115, 560, 250, 740), "G13_橡皮.png", 2.0),
        ((180, 650, 380, 840), "G13_钥匙与姓名牌.png", 1.8),
    ]:
        a = line * rect_alpha(roi.shape, box)
        w, h = save_rgba(os.path.join(DST, name), a, scale, soft=True)
        print("223636 %-22s %dx%d" % (name, w, h))
    a = a_pen(roi, (175, 330, 510, 745), (300, 520))
    w, h = save_rgba(os.path.join(DST, "G13_笔.png"), a, 1.8, soft=True)
    print("223636 %-22s %dx%d" % ("G13_笔.png", w, h))

    for tid, (name, fn, scale) in PLAN.items():
        a = fn(roi_of(tid))
        w, h = save_rgba(os.path.join(DST, name), a, scale, soft=True)
        print("%s %-24s %dx%d" % (tid[-6:], name, w, h))

    # 223706 不走线稿，输出灰度贴纸
    w, h = save_gray(os.path.join(DST, "G13_人物_黑衣.png"),
                     a_grayscale(roi_of("T20261028_223706")), 1.4)
    print("223706 %-24s %dx%d" % ("G13_人物_黑衣.png", w, h))


if __name__ == "__main__":
    main()
