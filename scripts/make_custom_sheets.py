# 2026/10/26 23:58:00 创建 —— 为 image/custom 生成缩略图总览，便于人工/视觉核对内容
import os, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
SRC = os.path.join(ROOT, "image", "custom")
OUT = os.path.join(ROOT, "tmp")
os.makedirs(OUT, exist_ok=True)

CELL, COLS, ROWS = 480, 5, 4
PER = COLS * ROWS
FONT = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
           r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(fp):
        FONT = ImageFont.truetype(fp, 20)
        break

files = sorted(os.listdir(SRC))
files = [f for f in files if os.path.splitext(f)[1].lower() in
         (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp")]

pages = []
for start in range(0, len(files), PER):
    chunk = files[start:start + PER]
    sheet = Image.new("RGB", (COLS * CELL, ROWS * CELL), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    for i, name in enumerate(chunk):
        idx = start + i + 1
        p = os.path.join(SRC, name)
        try:
            with Image.open(p) as im:
                im = im.convert("RGB")
                im.thumbnail((CELL - 12, CELL - 48), Image.LANCZOS)
                x = (i % COLS) * CELL
                y = (i // COLS) * CELL
                ox = x + (CELL - im.width) // 2
                oy = y + 30 + (CELL - 40 - im.height) // 2
                sheet.paste(im, (ox, oy))
        except Exception as e:
            print("ERR", name, e)
        x = (i % COLS) * CELL
        y = (i // COLS) * CELL
        dr.text((x + 6, y + 4), "%02d %s" % (idx, name[:34]), fill=(240, 240, 240), font=FONT)
        dr.text((x + 6, y + CELL - 20), name[34:68], fill=(170, 170, 170), font=FONT)
    out = os.path.join(OUT, "custom_sheet_%d.jpg" % (len(pages) + 1))
    sheet.save(out, quality=88)
    pages.append(out)
    print("wrote", out, sheet.size)

print("total files", len(files), "sheets", len(pages))
