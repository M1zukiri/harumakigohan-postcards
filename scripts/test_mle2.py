# 2026/10/28 04:00:00 用线稿模型复测其余素材（含饭团），与现有结果并列对比
import os
import sys

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_f3 import load_any, trim_bottom
from mle import manga_lines

TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers_f3")
D2 = os.path.join(ROOT, "postcards", "_workbench", "stickers", "Futarino2")
REVIEW = os.path.join(ROOT, "postcards", "_workbench", "out", "review_f3")


def to_view(ink):
    a = np.clip(ink * 255, 0, 255).astype(np.uint8)
    rgb = np.zeros((a.shape[0], a.shape[1], 3), np.uint8)
    im = Image.fromarray(np.dstack([rgb, a]), "RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, (0, 0), im)
    return bg


def panel(items, dst, cols=3, tile=(380, 300)):
    f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    tiles = []
    for im, label in items:
        W, H = im.size
        k = min((tile[0] - 12) / W, (tile[1] - 34) / H)
        im2 = im.resize((max(1, int(W * k)), max(1, int(H * k))), Image.LANCZOS)
        c = Image.new("RGB", tile, (255, 255, 255))
        c.paste(im2, (6, 24))
        ImageDraw.Draw(c).text((6, 4), label, fill=(30, 30, 30), font=f)
        tiles.append(c)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tile[0] * cols, tile[1] * rows), (235, 235, 238))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tile[0], (i // cols) * tile[1]))
    sheet.save(dst)
    return sheet.size


def existing(name, folder=OUT):
    p = os.path.join(folder, name)
    if not os.path.exists(p):
        return None
    return Image.open(p).convert("RGBA")


def run(tid, cur_name, tb=False):
    j, roi, box = load_any(tid)
    if tb:
        roi = trim_bottom(roi)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    ml = manga_lines(gray)
    ink = 1.0 - ml / 255.0
    items = [(Image.fromarray(roi[:, :, ::-1]).convert("RGB"), "原图")]
    cur = existing(cur_name)
    if cur is not None:
        bg = Image.new("RGB", cur.size, (255, 255, 255))
        bg.paste(cur, (0, 0), cur)
        items.append((bg, "现有 " + cur_name.replace(".png", "")))
    items.append((to_view(ink), "MangaLine 原始"))
    items.append((to_view(np.clip((ink - 0.10) / 0.70, 0, 1)), "MangaLine 收紧"))
    dst = os.path.join(REVIEW, "_retest_%s.png" % tid[-6:])
    print(tid, panel(items, dst))
    return dst


def run_onigiri():
    """饭团：用工作台提交的截图和手工蒙版，看线稿模型能否提取出更完整的轮廓。"""
    img = np.array(Image.open(os.path.join(TASKS, "M20261027_223312.png")).convert("RGB"))
    mk = np.array(Image.open(os.path.join(TASKS, "M20261027_223312_mask.png")).convert("RGBA"))
    painted = mk[..., 3] > 40
    keep = painted & (mk[..., 1] > 130) & (mk[..., 0] < 130)
    ys, xs = np.nonzero(keep)
    x0, x1 = max(0, xs.min() - 40), min(img.shape[1], xs.max() + 40)
    y0, y1 = max(0, ys.min() - 40), min(img.shape[0], ys.max() + 40)
    roi = img[y0:y1, x0:x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    ml = manga_lines(gray)
    ink = 1.0 - ml / 255.0
    # 蒙版限定区域
    m = np.zeros(roi.shape[:2], np.uint8)
    m[(keep[y0:y1, x0:x1])] = 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    from scipy import ndimage
    m = ndimage.binary_fill_holes(m.astype(bool)).astype(np.uint8)
    ink_masked = ink * m
    items = [
        (Image.fromarray(roi).convert("RGB"), "原图 ROI"),
        (to_view(ink), "MangaLine 全图"),
        (to_view(ink_masked), "MangaLine + 蒙版"),
    ]
    cur = existing("F2_饭团.png", D2)
    if cur is not None:
        bg = Image.new("RGB", cur.size, (255, 255, 255))
        bg.paste(cur, (0, 0), cur)
        items.append((bg, "现有 F2_饭团（径向补全）"))
    dst = os.path.join(REVIEW, "_retest_onigiri.png")
    print("onigiri", panel(items, dst, cols=2))
    return dst


if __name__ == "__main__":
    run("T20261027_232356", "F3_双人_提灯与书.png", True)
    run("T20261027_232610", "F3_人物_长椅与机器人.png", True)
    run("T20261027_232646", "F3_人物轮廓_坐姿.png")
    run("T20261027_232654", "F3_字迹_若能化作彗星.png")
    run("T20261027_232620", "F3_螃蟹.png")
    run("T20261027_232553", "F3_车站站牌.png")
    run("T20261027_232541", "F3_彗星.png")
    run_onigiri()
