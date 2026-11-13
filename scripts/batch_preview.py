# 2026-10-28 19:30:00 生成本批任务 ROI 的总览拼图，用于人工确认内容
import os
import json
import glob

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")


def load_roi(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGBA")
    r = j.get("rect")
    if r:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        x2, y2 = min(x + w, im.width), min(y + h, im.height)
        x, y = max(x, 0), max(y, 0)
        im = im.crop((x, y, x2, y2))
    return j, im


def main():
    os.makedirs(OUT, exist_ok=True)
    ids = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(TASKS, "T20261028_19*.json")))
    cell = 420
    cols = 5
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 26)), "white")
    dr = ImageDraw.Draw(sheet)
    for i, tid in enumerate(ids):
        j, im = load_roi(tid)
        im.thumbnail((cell - 8, cell - 8), Image.LANCZOS)
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 26)
        bg = Image.new("RGB", (cell - 8, cell - 8), (245, 245, 245))
        for yy in range(0, cell - 8, 16):
            for xx in range(0, cell - 8, 16):
                if (xx // 16 + yy // 16) % 2:
                    bg.paste((225, 225, 225), (xx, yy, min(xx + 16, cell - 8), min(yy + 16, cell - 8)))
        bg.paste(im, ((cell - 8 - im.width) // 2, (cell - 8 - im.height) // 2), im)
        sheet.paste(bg, (cx + 4, cy + 4))
        dr.text((cx + 6, cy + cell - 14), "%s  %s" % (tid[-6:], j.get("desc", "")[:14]), fill=(20, 20, 20))
    p = os.path.join(OUT, "_batch_overview.png")
    sheet.save(p)
    print(p, sheet.size)


if __name__ == "__main__":
    main()
