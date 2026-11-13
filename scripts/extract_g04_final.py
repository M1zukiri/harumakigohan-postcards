# 2026-10-28 21:00:00 G04-G07 组贴纸正式提取：按图类型分派方案，输出到贴纸库
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
GROUP = "G04-G07_コバルトメモリーズ_セブンティーナ"
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", GROUP)
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")

from extract_f2 import save_rgba, contour_alpha  # noqa: E402
from extract_f3 import mle_line, dark_lines, bright_lines  # noqa: E402


def roi_of(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def drop_edge_bands(a, band=0.12, cov=0.45):
    """清掉贴近画布边缘、几乎贯穿整行/整列的直线（截图边框）。"""
    h, w = a.shape
    bh, bw = max(4, int(h * band)), max(4, int(w * band))
    rows = (a > 40).mean(axis=1)
    cols = (a > 40).mean(axis=0)
    for y in range(h):
        if rows[y] > cov and (y < bh or y >= h - bh):
            a[max(0, y - 3):y + 4, :] = 0
    for x in range(w):
        if cols[x] > cov and (x < bw or x >= w - bw):
            a[:, max(0, x - 3):x + 4] = 0
    return a


def drop_long_straight(a, min_ratio=0.5, angle_tol=4.0, erase=8, edge=0.07):
    """只擦贴近画布边缘、接近水平/垂直的长直线（截图边框残留）。"""
    h, w = a.shape
    ref = max(h, w)
    binm = ((a > 12) * 255).astype(np.uint8)
    binm = cv2.dilate(binm, np.ones((3, 3), np.uint8))
    lines = cv2.HoughLinesP(binm, 1, np.pi / 180, threshold=int(ref * 0.30),
                            minLineLength=int(ref * min_ratio), maxLineGap=16)
    if lines is None:
        return a, 0
    n = 0
    for x1, y1, x2, y2 in lines[:, 0]:
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        ang = abs(np.degrees(np.arctan2(dy, dx)))
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if ang < angle_tol and (my < h * edge or my > h * (1 - edge)):
            cv2.line(a, (x1, y1), (x2, y2), 0, erase)
            n += 1
        elif ang > 90 - angle_tol and (mx < w * edge or mx > w * (1 - edge)):
            cv2.line(a, (x1, y1), (x2, y2), 0, erase)
            n += 1
    return a, n


def hsv_of(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    return [hsv[..., i].astype(np.int16) for i in range(3)]


def a_clahe(roi):
    return mle_line(roi, clahe=True) * 255.0


def a_low(roi):
    """弱线也收：阈值压到 0.006 / 0.30，补回手指、衣褶、面板格这类浅线。"""
    return mle_line(roi, thr=0.006, span=0.30, clahe=True) * 255.0


def a_multi(roi, scales=(0.75, 1.0, 1.5)):
    """多尺度取并集，减少细节随输入分辨率漂移。"""
    h, w = roi.shape[:2]
    acc = np.zeros((h, w), np.float32)
    for s in scales:
        if s == 1.0:
            sub, (dw, dh) = roi, (w, h)
        else:
            dw, dh = max(32, int(w * s)), max(32, int(h * s))
            sub = cv2.resize(roi, (dw, dh),
                             interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        l = mle_line(sub, thr=0.008, span=0.35, clahe=True)
        if (dw, dh) != (w, h):
            l = cv2.resize(l, (w, h), interpolation=cv2.INTER_LINEAR)
        acc = np.maximum(acc, l)
    return acc * 255.0


def a_hat(roi):
    """只有草帽：限暖色相，挡掉帽檐下露出的头部。"""
    H = hsv_of(roi)[0]
    warm = cv2.morphologyEx((H < 65).astype(np.uint8), cv2.MORPH_CLOSE,
                            np.ones((15, 15), np.uint8))
    warm = ndimage.binary_fill_holes(warm > 0).astype(np.float32)
    g = np.clip(cv2.GaussianBlur(warm, (0, 0), 6) * 1.8, 0, 1)
    return mle_line(roi, clahe=True) * 255.0 * g


def a_sign(roi):
    """路牌只有圆牌 + 立柱 + 方板，灌木与路面挡在几何掩膜外。"""
    h, w = roi.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (97, 110), (53, 79), 0, 0, 360, 1, -1)
    cv2.rectangle(m, (86, 172), (114, h - 1), 1, -1)
    cv2.rectangle(m, (56, 196), (133, 398), 1, -1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    g = np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3) * 2.4, 0, 1)
    a = mle_line(roi, clahe=True) * 255.0 * g
    a[m == 0] = 0
    a[398:, :] = 0
    a[196:, :56] = 0
    a[196:, 133:] = 0
    return a


def a_ticket(roi):
    """票面直线稿，用高饱和区抹掉两侧手指。"""
    line = mle_line(roi, clahe=True) * 255.0
    H, S, V = hsv_of(roi)
    allow = ((S > 45) & (H > 70) & (H < 120)).astype(np.uint8)
    allow = cv2.dilate(allow, np.ones((25, 25), np.uint8))
    g = cv2.GaussianBlur(allow.astype(np.float32), (0, 0), 7)
    return line * np.clip(g * 1.6, 0, 1)


def a_clock(roi):
    """闹钟：外壳直线稿 + 青色数码笔画。"""
    line = mle_line(roi, clahe=True) * 255.0
    H, S, V = hsv_of(roi)
    digits = ndimage.binary_closing((H > 80) & (H < 112) & (S > 70), np.ones((3, 3)))
    dig = np.clip(cv2.GaussianBlur(digits.astype(np.float32), (0, 0), 0.9) * 1.5, 0, 1) * 235
    return np.maximum(line * 0.9, dig)


def a_scene(roi):
    """粉色前景：云与鸟屋的色块边界描边 + 屋身窗户与蝴蝶结。"""
    H, S, V = hsv_of(roi)
    m = ndimage.binary_fill_holes(
        ndimage.binary_closing((H > 145) & (S > 50) & (V > 100), np.ones((7, 7))))
    edge = contour_alpha(m, 4.0, ss=4)
    out = edge.copy()

    # 屋身窗户是粉色区域里的暗洞，用它定位鸟屋
    hole = (V < 115) & m
    hole = ndimage.binary_opening(hole, np.ones((5, 5)))
    hole = ndimage.binary_fill_holes(hole)
    lab, n = ndimage.label(hole)
    if not n:
        return out
    sizes = ndimage.sum(hole, lab, range(1, n + 1))
    i = int(np.argmax(sizes)) + 1
    if sizes[i - 1] < 0.0008 * hole.size:
        return out
    ys, xs = np.nonzero(lab == i)
    cx, cy = int(xs.mean()), int(ys.mean())
    r = int(max(xs.max() - xs.min(), ys.max() - ys.min()) * 1.6) + 30
    x0, y0 = max(0, cx - r), max(0, cy - r)
    x1, y1 = min(roi.shape[1], cx + r), min(roi.shape[0], cy + r)

    # 窗户轮廓
    win = (lab == i).astype(np.uint8)
    out = np.clip(np.maximum(out, contour_alpha(win > 0, 2.6, ss=4)), 0, 255)

    # 蝴蝶结：屋身上的弱边，只在屋身内部取，避免把屋边当成线条
    sub = roi[y0:y1, x0:x1]
    inside = ndimage.binary_erosion(m, np.ones((17, 17)))[y0:y1, x0:x1]
    inside = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 5)
    inner = dark_lines(sub, sigma=3, t1=0.8, t2=5.0) * 255.0 * np.clip(inside * 1.5, 0, 1)
    pad = np.zeros_like(out)
    pad[y0:y1, x0:x1] = inner
    return np.clip(np.maximum(out, pad * 0.9), 0, 255)


FRAME_EDGE = {"T20261028_190938", "T20261028_191201", "T20261028_191238"}
FRAME_LONG = {"T20261028_190908", "T20261028_191004", "T20261028_191020",
              "T20261028_191030", "T20261028_191042", "T20261028_191133",
              "T20261028_191238", "T20261028_190956", "T20261028_190921"}

PLAN = {
    "T20261028_190853": ("G04_人物_收听电台.png", a_low, 1.4),
    "T20261028_190908": ("G04_草帽.png", a_hat, 1.8),
    "T20261028_190921": ("G04_人物_背影与琴箱.png", a_clahe, 1.5),
    "T20261028_190930": ("G04_人物_草帽与长裙.png", a_clahe, 1.5),
    "T20261028_190938": ("G04_人物_仰卧特写.png",
                         lambda r: dark_lines(r, sigma=4, t1=2.0, t2=9.0) * 255.0, 1.3),
    "T20261028_190956": ("G04_双人_吉他与草帽.png", a_multi, 1.6),
    "T20261028_191004": ("G04_人物_微笑特写.png", a_clahe, 1.2),
    "T20261028_191020": ("G04_鸽子_伏地.png", a_low, 1.5),
    "T20261028_191030": ("G04_鸽子_屋顶.png", a_low, 1.4),
    "T20261028_191042": ("G04_蝴蝶结.png", a_clahe, 1.8),
    "T20261028_191052": ("G04_手机.png", a_clahe, 2.4),
    "T20261028_191102": ("G04_罐头.png", a_clahe, 2.0),
    "T20261028_191111": ("G04_路牌.png", a_sign, 1.6),
    "T20261028_191133": ("G04_演出票.png", a_ticket, 1.5),
    "T20261028_191149": ("G04_字迹_Seventina.png", lambda r: bright_lines(r, 110) * 255.0, 1.6),
    "T20261028_191201": ("G04_时钟.png", a_clahe, 1.6),
    "T20261028_191212": ("G04_闹钟.png", a_clock, 1.5),
    "T20261028_191223": ("G04_窗户.png", a_clahe, 1.6),
    "T20261028_191238": ("G04_前景_窗前.png", a_scene, 1.3),
}


def main(only=None):
    os.makedirs(DST, exist_ok=True)
    for tid, (name, fn, scale) in PLAN.items():
        if only and tid not in only:
            continue
        a = fn(roi_of(tid))
        if tid in FRAME_EDGE:
            a = drop_edge_bands(a)
        if tid in FRAME_LONG:
            a, n = drop_long_straight(a)
        p = os.path.join(DST, name)
        w, h = save_rgba(p, a, scale, soft=True)
        print("%s  %-28s %4dx%-4d" % (tid[-6:], name, w, h))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
