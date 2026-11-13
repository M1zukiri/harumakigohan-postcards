# 2026-10-28 19:50:00 输出指定任务的原始 ROI，供人工核对细节
import os
import sys
import json

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")


def main(ids):
    os.makedirs(OUT, exist_ok=True)
    for tid in ids:
        j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
        im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
        r = j.get("rect")
        if r:
            x, y = max(r["x"], 0), max(r["y"], 0)
            im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
        p = os.path.join(OUT, "_src_" + tid + ".png")
        im.save(p)
        print(p, im.size)


if __name__ == "__main__":
    main(sys.argv[1:])
