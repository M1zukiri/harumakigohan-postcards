# 2026-10-29 20:10:00 生成 G21 任务 ROI 总览，确认每个任务的内容与尺寸
import os
import json
import glob

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g21")


def load_roi(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGBA")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return j, im


def checker(w, h, s=12):
    bg = Image.new("RGB", (w, h), (248, 248, 248))
    c = Image.new("RGB", (w, h), (224, 224, 224))
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                md.rectangle([x, y, x + s - 1, y + s - 1], fill=255)
    bg.paste(c, (0, 0), m)
    return bg


def main():
    os.makedirs(OUT, exist_ok=True)
    ids = sorted(os.path.basename(p)[:-5] for p in
                 glob.glob(os.path.join(TASKS, "T20261029_1955*.json")) +
                 glob.glob(os.path.join(TASKS, "T20261029_1954*.json")) +
                 glob.glob(os.path.join(TASKS, "T20261029_1953*.json")) +
                 glob.glob(os.path.join(TASKS, "T20261029_1952*.json")) +
                 glob.glob(os.path.join(TASKS, "T20261029_1951*.json")))
    cell, cols = 440, 5
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 26)), "white")
    dr = ImageDraw.Draw(sheet)
    for i, tid in enumerate(ids):
        j, im = load_roi(tid)
        print("%s %-14s %s" % (tid[-6:], str(im.size), j.get("desc", "")[:34]))
        im.thumbnail((cell - 10, cell - 10), Image.LANCZOS)
        tile = checker(cell, cell)
        tile.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 26)
        sheet.paste(tile, (cx + 2, cy + 2))
        dr.text((cx + 6, cy + cell + 4), "%s %s" % (tid[-6:], j.get("desc", "")[:20]),
                fill=(10, 10, 10))
    p = os.path.join(OUT, "_overview.png")
    sheet.save(p)
    print(p, sheet.size)


if __name__ == "__main__":
    main()
