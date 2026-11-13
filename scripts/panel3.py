# 2026-10-28 20:10:00 生成「原图 / 方案A / 方案B」三栏对比图
import os
import sys
import glob

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")


def white_bg(im, w, h):
    bg = Image.new("RGB", (w, h), (250, 250, 250))
    c = Image.new("RGB", (w, h), (222, 222, 222))
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    for y in range(0, h, 14):
        for x in range(0, w, 14):
            if (x // 14 + y // 14) % 2:
                md.rectangle([x, y, x + 13, y + 13], fill=255)
    bg.paste(c, (0, 0), m)
    bg.paste(im, ((w - im.width) // 2, (h - im.height) // 2), im)
    return bg


def panel(rows, dst, cell=430, tags=("src", "base", "clahe")):
    n = len(rows)
    W = cell * len(tags)
    H = n * (cell + 20)
    out = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(out)
    for r, tid in enumerate(rows):
        for c, tag in enumerate(tags):
            p = os.path.join(REV, "_%s_%s.png" % (tag, tid))
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGBA")
            im.thumbnail((cell - 10, cell - 10), Image.LANCZOS)
            out.paste(white_bg(im, cell, cell), (c * cell, r * (cell + 20)))
        dr.text((6, r * (cell + 20) + cell + 4), tid[-6:], fill=(0, 0, 0))
    out.save(dst)
    print(dst, out.size)


if __name__ == "__main__":
    ids = sorted(os.path.basename(p)[:-4].replace("_base_", "")
                 for p in glob.glob(os.path.join(REV, "_base_T20261028_*.png")))
    half = (len(ids) + 1) // 2
    panel(ids[:half], os.path.join(REV, "_cmp_a.png"))
    panel(ids[half:], os.path.join(REV, "_cmp_b.png"))
