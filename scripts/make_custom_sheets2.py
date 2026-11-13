# 2026/10/27 03:45:00 创建 —— 独立 custom 图片（去重后）生成大图网格，便于逐张识别归属
import os, json, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
OUT = os.path.join(ROOT, "tmp")
os.makedirs(OUT, exist_ok=True)

info = json.load(open(os.path.join(M, "custom-vs-pixiv.json"), encoding="utf-8"))
dims = {r["file"]: r for r in json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
        if r["dir"] == "custom"}
uniq = [x["file"] for x in info if not x["dup"]]
uniq.sort()

CELL, COLS, ROWS = 760, 3, 3
PER = COLS * ROWS
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)
SMALL = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)

pages = []
for start in range(0, len(uniq), PER):
    chunk = uniq[start:start + PER]
    sheet = Image.new("RGB", (COLS * CELL, ROWS * CELL), (20, 20, 24))
    dr = ImageDraw.Draw(sheet)
    for i, name in enumerate(chunk):
        idx = start + i + 1
        x = (i % COLS) * CELL
        y = (i // COLS) * CELL
        box = CELL - 66
        try:
            with Image.open(os.path.join(ROOT, "image", "custom", name)) as im:
                im = im.convert("RGB")
                im.thumbnail((box, box), Image.LANCZOS)
                ox = x + (CELL - im.width) // 2
                oy = y + 34 + (box - im.height) // 2
                sheet.paste(im, (ox, oy))
        except Exception as e:
            dr.text((x + 10, y + 80), "ERR", fill=(255, 120, 120), font=SMALL)
        d = dims[name]
        dr.text((x + 8, y + 6), "%02d  %s" % (idx, name[:40]), fill=(240, 240, 240), font=FONT)
        dr.text((x + 8, y + CELL - 28), "%dx%d  %.1fMB" % (d["w"], d["h"], d["bytes"] / 1048576),
                fill=(150, 170, 190), font=SMALL)
    out = os.path.join(OUT, "custom_uniq_%d.jpg" % (len(pages) + 1))
    sheet.save(out, quality=88)
    pages.append(out)
    print("wrote", out, sheet.size, len(chunk), "cells")
print("uniq total", len(uniq), "sheets", len(pages))
