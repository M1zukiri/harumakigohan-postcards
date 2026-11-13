# 2026-10-28 19:45:00 把一批 PNG 拼成总览图，用于逐张比对提取结果
import os
import sys
import glob

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sheet(paths, dst, cell=420, cols=5, checker=True):
    rows = (len(paths) + cols - 1) // cols
    im0 = Image.new("RGB", (cols * cell, rows * (cell + 26)), "white")
    dr = ImageDraw.Draw(im0)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGBA")
        im.thumbnail((cell - 8, cell - 8), Image.LANCZOS)
        bg = Image.new("RGB", (cell - 8, cell - 8), (247, 247, 247))
        if checker:
            c = Image.new("RGB", (cell - 8, cell - 8), (223, 223, 223))
            m = Image.new("L", (cell - 8, cell - 8), 0)
            md = ImageDraw.Draw(m)
            for y in range(0, cell - 8, 16):
                for x in range(0, cell - 8, 16):
                    if (x // 16 + y // 16) % 2:
                        md.rectangle([x, y, x + 15, y + 15], fill=255)
            bg.paste(c, (0, 0), m)
        bg.paste(im, ((cell - 8 - im.width) // 2, (cell - 8 - im.height) // 2), im)
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 26)
        im0.paste(bg, (cx + 4, cy + 4))
        dr.text((cx + 6, cy + cell - 14), os.path.basename(p).replace("_base_T20261028_", "")[:-4],
                fill=(20, 20, 20))
    im0.save(dst)
    print(dst, len(paths), im0.size)


if __name__ == "__main__":
    rev = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")
    ps = sorted(glob.glob(os.path.join(rev, "_base_T20261028_*.png")))
    sheet(ps, os.path.join(rev, "_base_overview.png"))
