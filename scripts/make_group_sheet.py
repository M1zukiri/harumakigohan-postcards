# 2026/10/27 02:40:00 创建 —— 25 个素材组总览：有插画用插画，缺插画用 MV 帧
import os, json, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
rows = json.load(open(os.path.join(M, "postcard-song-groups.json"), encoding="utf-8"))

CELL_W, CELL_H, COLS = 480, 470, 5
PAD = 12
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
SMALL = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)

nrows = (len(rows) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * CELL_W, nrows * CELL_H), (22, 22, 26))
dr = ImageDraw.Draw(sheet)

for i, r in enumerate(rows):
    x = (i % COLS) * CELL_W
    y = (i // COLS) * CELL_H
    box_h = CELL_H - 78
    if r["status"] == "ready":
        src = os.path.join(ROOT, "image", "pixiv", r["img"][0]["file"])
        caption = "插画：" + r["img"][0]["title"][:24]
    else:
        src = os.path.join(ROOT, "tmp", "mvshots", r["song_id"] + ".jpg")
        caption = "MV 帧（缺插画）"
    try:
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((CELL_W - 2 * PAD, box_h), Image.LANCZOS)
            ox = x + (CELL_W - im.width) // 2
            oy = y + 8 + (box_h - im.height) // 2
            sheet.paste(im, (ox, oy))
    except Exception as e:
        dr.text((x + PAD, y + 80), "ERR " + str(e)[:24], fill=(255, 110, 110), font=SMALL)
    color = (245, 245, 245) if r["status"] == "ready" else (255, 190, 120)
    dr.text((x + PAD, y + CELL_H - 70), "%s  %s" % (r["group"], r["title"][:22]),
            fill=color, font=FONT)
    dr.text((x + PAD, y + CELL_H - 40), caption, fill=(155, 175, 195), font=SMALL)

out = os.path.join(ROOT, "tmp", "song_groups_sheet.jpg")
sheet.save(out, quality=90)
print("wrote", out, sheet.size, "groups", len(rows))
