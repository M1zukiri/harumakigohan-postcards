# 2026/10/28 02:10:00 Futarino3 提取任务：深蓝底发光线条与低对比人物，输出纯黑白线稿
import os
import sys
import json

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers_f3")
REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f3")
os.makedirs(OUT, exist_ok=True)
os.makedirs(REVIEW, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_f2 import (imread, save_rgba, keep_components, contour_alpha,
                        inner_dog, preview)


def load_any(tid):
    """rect 为 null 时用整张截图。"""
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    bgr = imread(os.path.join(TASKS, j["image_file"]))
    r = j.get("rect")
    if not r:
        return j, bgr, (0, 0, bgr.shape[1], bgr.shape[0])
    h, w = bgr.shape[:2]
    x0 = max(0, r["x"]); y0 = max(0, r["y"])
    x1 = min(w, r["x"] + r["w"]); y1 = min(h, r["y"] + r["h"])
    return j, bgr[y0:y1, x0:x1].copy(), (x0, y0, x1, y1)


def stats(name, roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V = hsv[..., 2]
    S = hsv[..., 1]
    q = np.percentile(V, [1, 10, 25, 50, 75, 90, 99]).astype(int)
    print("  %-10s V%%=%s  S中位=%d" % (name, list(map(int, q)), int(np.median(S))))


def bright_lines(roi, thr=170, min_area=6, thick=1, sat_max=255):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    S = hsv[..., 1].astype(np.int16)
    V = hsv[..., 2].astype(np.int16)
    m = (V > thr) & (S <= sat_max)
    m = keep_components(m, min_area)
    a = (m * 255).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    if thick > 1:
        a = cv2.dilate(a, np.ones((2, 2), np.uint8), iterations=thick - 1)
    return a.astype(np.float32)


def dark_lines(roi, sigma=5, t1=3.0, t2=14.0, mask=None):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), sigma)
    dog = blur - gray
    line = np.clip((dog - t1) / max(t2 - t1, 1e-3), 0, 1)
    if mask is not None:
        line = line * mask.astype(np.float32)
    return line


def norm_stroke(line, thr=0.35, w=2):
    from skimage.morphology import skeletonize
    b = (line > thr).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    sk = skeletonize(b)
    return cv2.dilate(sk.astype(np.uint8) * 255, np.ones((w, w), np.uint8)).astype(np.float32) / 255.0


def remove_long_lines(line, min_len=55, gap=6, thick=5):
    """去掉光照边界这类长直线，保留短而弯的字迹。"""
    b = (line > 0.35).astype(np.uint8) * 255
    lines = cv2.HoughLinesP(b, 1, np.pi / 180, threshold=36,
                            minLineLength=min_len, maxLineGap=gap)
    if lines is None:
        return line
    out = b.copy()
    for x1, y1, x2, y2 in lines[:, 0]:
        cv2.line(out, (int(x1), int(y1)), (int(x2), int(y2)), 0, thick)
    return (out > 0).astype(np.float32)


def drop_horizontal(bin_img, k=7):
    """去掉横向密集扫描线，纵向块状结构保留。"""
    b = (bin_img > 0.35).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((k, 1), np.uint8))
    return b.astype(np.float32)


def remove_horizontals(line, k=200):
    """只去掉横穿整幅画面的长光带；角色轮廓里的短水平线不动。"""
    b = (line > 0.35).astype(np.uint8) * 255
    hor = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((1, k), np.uint8))
    hor = cv2.dilate(hor, np.ones((7, 7), np.uint8))
    return ((b.astype(np.int16) - hor.astype(np.int16)) > 0).astype(np.float32)


def trim_bottom(roi, px=46):
    """截掉截图底部的字幕行。"""
    if roi.shape[0] > px * 3:
        return roi[:roi.shape[0] - px].copy()
    return roi


# ================= 任务 =================

def t_232646():
    """黑底蓝色发光线稿：角色坐在长椅上。"""
    j, roi, box = load_any("T20261027_232646")
    stats("232646", roi)
    a = mle_line(roi) * 255
    p = os.path.join(OUT, "F3_人物轮廓_坐姿.png")
    w, h = save_rgba(p, a, 1.5, soft=True)
    return p, "T232646 人物轮廓", (w, h)


def t_232654():
    """深蓝底白色手写字。"""
    j, roi, box = load_any("T20261027_232654")
    stats("232654", roi)
    a = bright_lines(roi, thr=165, min_area=6, thick=1)
    p = os.path.join(OUT, "F3_字迹_若能化作彗星.png")
    w, h = save_rgba(p, a, 2.0)
    return p, "T232654 字迹", (w, h)


def t_232448():
    """浅蓝纸面上的深色手写字迹。"""
    j, roi, box = load_any("T20261027_232448")
    stats("232448", roi)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    V = hsv[..., 2].astype(np.int16)
    a = sauvola_line(roi, win=25, k=0.10) * 255
    p = os.path.join(OUT, "F3_字迹_彗星になったなら.png")
    w, h = save_rgba(p, a * 255, 1.6)
    return p, "T232448 手写字", (w, h)


def t_232620():
    """深蓝海底的发光螃蟹：亮蓝描边。"""
    j, roi, box = load_any("T20261027_232620")
    stats("232620", roi)
    a = mle_line(roi) * 255
    p = os.path.join(OUT, "F3_螃蟹.png")
    w, h = save_rgba(p, a, 1.6, soft=True)
    return p, "T232620 螃蟹", (w, h)


def t_232541():
    """蓝背景上的彗星轨迹：绿色亮线 + 红色虚线。"""
    j, roi, box = load_any("T20261027_232541")
    stats("232541", roi)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    m = V > 178
    m = keep_components(m, 6)
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = gray[y0:y1, x0:x1]
    lo, hi = np.percentile(sub, [3, 98])
    g = np.clip((sub - lo) / max(hi - lo, 1e-3), 0, 1)
    ink = np.clip((g - 0.30) / 0.70, 0, 1)
    mm = m[y0:y1, x0:x1]
    ink = ink * mm.astype(np.float32)
    p = os.path.join(OUT, "F3_彗星.png")
    w, h = save_rgba(p, ink * 255, 1.5)
    return p, "T232541 彗星", (w, h)


def t_232635():
    """深蓝装置中央的发光屏幕。"""
    j, roi, box = load_any("T20261027_232635")
    stats("232635", roi)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    S, V = hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    m = (V > 205) & (S > 120)
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    line = contour_alpha(m, 4, ss=4) * 0.9
    Vs = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[..., 2]
    inner = ((Vs > 232) & m).astype(np.uint8)
    lab, n = ndimage.label(inner)
    keep = np.zeros_like(inner)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 10:
            continue
        if xs.max() - xs.min() > 110:
            continue
        keep[lab == i] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    a = np.clip(np.maximum(line, keep.astype(np.float32) * 0.95), 0, 1)
    p = os.path.join(OUT, "F3_屏幕.png")
    w, h = save_rgba(p, a * 255, 1.5)
    return p, "T232635 屏幕", (w, h)


def t_232553():
    """夜色中的车站站牌：圆牌 + 立柱 + 下方广告牌。"""
    j, roi, box = load_any("T20261027_232553")
    stats("232553", roi)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    S, V = hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    line = mle_line(roi)
    p = os.path.join(OUT, "F3_车站站牌.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232553 车站站牌", (w, h)


def t_232307():
    """整张风景：不做勾线，转黑白 + 拉对比度 + 近白归白。"""
    j, roi, box = load_any("T20261027_232307")
    stats("232307", roi)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lo, hi = np.percentile(gray, [2, 99])
    g = np.clip((gray - lo) / max(hi - lo, 1e-3), 0, 1)
    g = np.power(g, 1.25)
    thr = max(0.42, float(np.percentile(g, 62)))
    ink = np.clip((thr - g) / max(thr, 1e-3), 0, 1)
    ink = np.clip(ink * 1.55, 0, 1)
    ink[g > 0.93] = 0.0
    p = os.path.join(OUT, "F3_风景_近白归白.png")
    w, h = save_rgba(p, ink * 255, 1.5)
    return p, "T232307 风景黑白", (w, h)


def edge_blackhat(roi, k=15, thr=8.0, span=30.0, light_ratio=0.55):
    """形态学黑帽/白帽提取细线：阶跃边缘和细线响应强，缓慢的光影渐变几乎不响应。"""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    dark = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kern)
    light = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kern)
    both = np.maximum(dark, light * light_ratio)
    return np.clip((both - thr) / max(span, 1e-3), 0, 1)


def mle_line(roi, thr=0.02, span=0.55, clahe=False, clip=2.5):
    """MangaLineExtraction（SIGGRAPH 2017）：从彩色画面提取手绘结构线。

    thr / span 压得很低，先保证弱线不丢，缺失的线条只能手画、多留的可以手擦。
    clahe 只对暗部人物图开，用来把深色身体与深色背景之间那点弱描边抬起来；
    对发光体和高对比场景开它会把噪声一起放大，所以默认关闭。"""
    from mle import manga_lines
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    src = gray
    if clahe:
        src = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray)
    ml = manga_lines(src)
    ink = 1.0 - ml / 255.0
    return np.clip((ink - thr) / max(span, 1e-3), 0, 1)


def sauvola_line(roi, win=25, k=0.10):
    """Sauvola 局部阈值：适合浅底深字的字迹提取，笔画比线稿模型更粗更实。"""
    from skimage.filters import threshold_sauvola
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    t = threshold_sauvola(gray, window_size=win, k=k)
    return (gray < t).astype(np.float32)


def t_232329():
    """夜色中的人物侧脸 + 右下小机器人 + 右侧墙壁。"""
    j, roi, box = load_any("T20261027_232329")
    roi = trim_bottom(roi)
    stats("232329", roi)
    line = mle_line(roi, clahe=True)
    p = os.path.join(OUT, "F3_人物_侧脸与机器人.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232329 人物与机器人", (w, h)


def t_232356():
    """两个女孩：一个提灯笼，一个捧书。"""
    j, roi, box = load_any("T20261027_232356")
    roi = trim_bottom(roi)
    stats("232356", roi)
    line = mle_line(roi, clahe=True)
    p = os.path.join(OUT, "F3_双人_提灯与书.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232356 双人", (w, h)


def t_232423():
    """靠窗的侧脸女孩与背后座椅。"""
    j, roi, box = load_any("T20261027_232423")
    stats("232423", roi)
    line = mle_line(roi, clahe=True)
    p = os.path.join(OUT, "F3_人物_靠窗侧脸.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232423 靠窗人物", (w, h)


def t_232520():
    """车内人物与旁边的购物袋、机器人。"""
    j, roi, box = load_any("T20261027_232520")
    roi = trim_bottom(roi)
    stats("232520", roi)
    line = mle_line(roi, clahe=True)
    p = os.path.join(OUT, "F3_人物_车内与购物袋.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232520 车内人物", (w, h)


def t_232610():
    """车站长椅上的人、机器人和长椅。"""
    j, roi, box = load_any("T20261027_232610")
    roi = trim_bottom(roi)
    stats("232610", roi)
    line = mle_line(roi, clahe=True)
    p = os.path.join(OUT, "F3_人物_长椅与机器人.png")
    w, h = save_rgba(p, line * 255, 1.4, soft=True)
    return p, "T232610 长椅人物", (w, h)


JOBS = {
    "232329": t_232329,
    "232356": t_232356,
    "232423": t_232423,
    "232520": t_232520,
    "232610": t_232610,
    "232646": t_232646,
    "232654": t_232654,
    "232448": t_232448,
    "232620": t_232620,
    "232541": t_232541,
    "232635": t_232635,
    "232553": t_232553,
    "232307": t_232307,
}


if __name__ == "__main__":
    keys = sys.argv[1:] or list(JOBS)
    items = []
    for k in keys:
        try:
            p, label, size = JOBS[k]()
            items.append((p, label, size))
            print("ok", os.path.basename(p), size)
        except Exception as e:
            print("FAIL", k, e)
            import traceback
            traceback.print_exc()
    if items:
        print(preview(items, os.path.join(REVIEW, "_preview.png")))
