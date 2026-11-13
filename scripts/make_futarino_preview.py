# 2026/10/27 05:10:00 创建 —— ふたりの专辑相关 A 档插画的色调预览，用于 Futarino1~3 分组
import os, json, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
OUT = os.path.join(ROOT, "tmp", "futarino_preview.jpg")

CAND = [
    ("90713756_p0.png", "僕たちの約束", "約束"),
    ("121941726_p0.jpg", "The Promise", "約束"),
    ("123932226_p0.jpg", "海辺の返信", "約束"),
    ("102116342_p0.png", "龍使いの未練", "約束"),
    ("103086244_p0.png", "リリナナみかげ", "秘密／彗星"),
]
CELL_W, CELL_H = 560, 520
COL = 3
font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
small = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
rows = (len(CAND) + COL - 1) // COL
sheet = Image.new("RGB", (COL * CELL_W, rows * CELL_H), (20, 20, 24))
dr = ImageDraw.Draw(sheet)
for i, (f, title, song) in enumerate(CAND):
    x = (i % COL) * CELL_W
    y = (i // COL) * CELL_H
    with Image.open(os.path.join(ROOT, "image", "pixiv", f)) as im:
        im = im.convert("RGB")
        im.thumbnail((CELL_W - 20, CELL_H - 90), Image.LANCZOS)
        sheet.paste(im, (x + (CELL_W - im.width) // 2, y + 10 + (CELL_H - 90 - im.height) // 2))
    dr.text((x + 10, y + CELL_H - 74), "%s" % title, fill=(245, 245, 245), font=font)
    dr.text((x + 10, y + CELL_H - 42), "%s　%s" % (song, f), fill=(150, 175, 200), font=small)
sheet.save(OUT, quality=90)
print("wrote", OUT, sheet.size)
