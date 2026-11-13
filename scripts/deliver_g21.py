# 2026-10-29 21:00:00 生成 G21 交付对比图：每格左原图右贴纸
import os
import json

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g21")
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", "G21_ゼロトーキング")

PAIRS = [
    ("T20261029_195142", "G21_四叶草.png"),
    ("T20261029_195153", "G21_字迹_ZeloTalking.png"),
    ("T20261029_195202", "G21_花束.png"),
    ("T20261029_195219", "G21_拖地的小人.png"),
    ("T20261029_195238", "G21_人物_带子.png"),
    ("T20261029_195249", "G21_人物_金发.png"),
    ("T20261029_195258", "G21_花朵.png"),
    ("T20261029_195307", "G21_眼睛_大.png"),
    ("T20261029_195310", "G21_眼睛_小.png"),
    ("T20261029_195328", "G21_卡片与字迹.png"),
    ("T20261029_195450", "G21_双人_白裙与蓝衣.png"),
    ("T20261029_195457", "G21_人物_表情.png"),
    ("T20261029_195506", "G21_人物_侧脸.png"),
    ("T20261029_195509", "G21_人物_低头.png"),
    ("T20261029_195511", "G21_人物_纸袋.png"),
    ("T20261029_195514", "G21_人物_跳跃.png"),
]
SIX = ["G21_六人_%02d.png" % i for i in range(1, 7)]


def roi(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGBA")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return im


def checker(w, h, s=12):
    bg = Image.new("RGB", (w, h), (250, 250, 250))
    c = Image.new("RGB", (w, h), (222, 222, 222))
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                md.rectangle([x, y, x + s - 1, y + s - 1], fill=255)
    bg.paste(c, (0, 0), m)
    return bg


def put(out, im, x, y, w, h):
    im = im.copy()
    im.thumbnail((w - 8, h - 8), Image.LANCZOS)
    tile = checker(w, h)
    tile.paste(im, ((w - im.width) // 2, (h - im.height) // 2), im)
    out.paste(tile, (x + 2, y + 2))


def main(cols=4, cell=470, half=233):
    rows = (len(PAIRS) + 1 + cols - 1) // cols + 1
    out = Image.new("RGB", (cols * cell, rows * (cell + 22)), "white")
    dr = ImageDraw.Draw(out)
    i = 0
    for tid, name in PAIRS:
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 22)
        put(out, roi(tid), cx, cy, half, half)
        put(out, Image.open(os.path.join(DST, name)).convert("RGBA"),
            cx + half, cy, half, half)
        dr.text((cx + 6, cy + half + 8), "%s %s" % (tid[-6:], name[4:-4]), fill=(0, 0, 0))
        i += 1
    # 195431 单独一行展示六张
    base = (i // cols) * (cell + 22)
    for k, name in enumerate(SIX):
        cx = (k % cols) * cell
        cy = base + (k // cols) * (cell + 22)
        put(out, Image.open(os.path.join(DST, name)).convert("RGBA"), cx, cy, cell, cell)
        dr.text((cx + 6, cy + cell - 6), name[4:-4], fill=(0, 0, 0))
    p = os.path.join(REV, "_deliver.png")
    out.save(p)
    print(p, out.size)


if __name__ == "__main__":
    main()
