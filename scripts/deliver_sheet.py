# 2026-10-28 22:05:00 生成「原始截图 / 提取贴纸」网格交付图，每格左原图右贴纸
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers",
                   "G04-G07_コバルトメモリーズ_セブンティーナ")

JOBS = [
    ("190853", "G04_人物_收听电台.png"),
    ("190908", "G04_草帽.png"),
    ("190921", "G04_人物_背影与琴箱.png"),
    ("190930", "G04_人物_草帽与长裙.png"),
    ("190938", "G04_人物_仰卧特写.png"),
    ("190956", "G04_双人_吉他与草帽.png"),
    ("191004", "G04_人物_微笑特写.png"),
    ("191020", "G04_鸽子_伏地.png"),
    ("191030", "G04_鸽子_屋顶.png"),
    ("191042", "G04_蝴蝶结.png"),
    ("191052", "G04_手机.png"),
    ("191102", "G04_罐头.png"),
    ("191111", "G04_路牌.png"),
    ("191133", "G04_演出票.png"),
    ("191149", "G04_字迹_Seventina.png"),
    ("191201", "G04_时钟.png"),
    ("191212", "G04_闹钟.png"),
    ("191223", "G04_窗户.png"),
    ("191238", "G04_前景_窗前.png"),
]


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


def main(cols=5, cell=440, half=214):
    rows = (len(JOBS) + cols - 1) // cols
    W, H = cols * cell, rows * (cell + 20)
    out = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(out)
    for i, (k, name) in enumerate(JOBS):
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 20)
        for c, p in enumerate((os.path.join(REV, "_src_T20261028_%s.png" % k),
                               os.path.join(DST, name))):
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGBA")
            im.thumbnail((half - 8, half - 8), Image.LANCZOS)
            tile = checker(half, half)
            tile.paste(im, ((half - im.width) // 2, (half - im.height) // 2), im)
            out.paste(tile, (cx + 2 + c * half, cy + 2))
        dr.text((cx + 6, cy + half + 6), "%s  %s" % (k, name[4:-4]), fill=(0, 0, 0))
    p = os.path.join(REV, "_deliver.png")
    out.save(p)
    print(p, out.size)


if __name__ == "__main__":
    main()
