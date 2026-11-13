# 2026-10-29 01:05:00 生成 G13 交付对比图，每格左原图右贴纸
import os
import json

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g13")
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", "G13_第三の心臓")

PAIRS = [
    ("T20261028_223420", "G13_书包.png"),
    ("T20261028_223447", "G13_人物_绿领巾少女.png"),
    ("T20261028_223500", "G13_双人_背影.png"),
    ("T20261028_223528", "G13_心脏.png"),
    ("T20261028_223541", "G13_人物_云霄.png"),
    ("T20261028_223553", "G13_人物_背影与书包.png"),
    ("T20261028_223602", "G13_人物_刘海侧身.png"),
    ("T20261028_223706", "G13_人物_黑衣.png"),
    ("T20261028_223715", "G13_字迹_第三の心臓.png"),
    ("T20261028_223724", "G13_插画_心形与两人.png"),
]
EXTRA = [("T20261028_223636", n) for n in
         ("G13_铅笔袋.png", "G13_笔.png", "G13_橡皮.png", "G13_钥匙与姓名牌.png")]


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


def main(cols=4, cell=480, half=232):
    rows = (len(PAIRS) + len(EXTRA) + cols - 1) // cols
    out = Image.new("RGB", (cols * cell, rows * (cell + 22)), "white")
    dr = ImageDraw.Draw(out)
    i = 0
    for tid, name in PAIRS:
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 22)
        for c, im in enumerate((roi(tid), Image.open(os.path.join(DST, name)).convert("RGBA"))):
            im = im.copy()
            im.thumbnail((half - 8, half - 8), Image.LANCZOS)
            tile = checker(half, half)
            tile.paste(im, ((half - im.width) // 2, (half - im.height) // 2), im)
            out.paste(tile, (cx + 2 + c * half, cy + 2))
        dr.text((cx + 6, cy + half + 8), "%s %s" % (tid[-6:], name[4:-4]), fill=(0, 0, 0))
        i += 1
    for tid, name in EXTRA:
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 22)
        im = Image.open(os.path.join(DST, name)).convert("RGBA")
        im.thumbnail((cell - 14, cell - 14), Image.LANCZOS)
        tile = checker(cell - 8, cell - 8)
        tile.paste(im, ((cell - 8 - im.width) // 2, (cell - 8 - im.height) // 2), im)
        out.paste(tile, (cx + 2, cy + 2))
        dr.text((cx + 6, cy + cell - 6), name[4:-4], fill=(0, 0, 0))
        i += 1
    p = os.path.join(REV, "_deliver.png")
    out.save(p)
    print(p, out.size)


if __name__ == "__main__":
    main()
