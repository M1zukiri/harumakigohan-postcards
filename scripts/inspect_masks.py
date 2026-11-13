# 2026-10-28 21:20:00 查看蒙版任务的保留区与原始截图
import os
import sys
import json

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")


def main():
    os.makedirs(OUT, exist_ok=True)
    for tid in ("M20261027_223312", "M20261027_223914", "M20261027_223955"):
        j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
        src = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
        msk = Image.open(os.path.join(TASKS, j["mask_file"]))
        m = np.array(msk.convert("RGBA"))
        print(tid, j["group"], src.size, msk.mode, msk.size)
        a = m[..., 3]
        print("   alpha>0 frac", round(float((a > 0).mean()), 4),
              " rgb uniq", len(np.unique(m[..., :3].reshape(-1, 3), axis=0)))
        vis = src.copy()
        tint = Image.new("RGB", src.size, (255, 0, 0))
        vis.paste(tint, (0, 0), msk.convert("L"))
        vis.save(os.path.join(OUT, "_mask_" + tid + ".png"))
        print("   ->", os.path.join(OUT, "_mask_" + tid + ".png"))


if __name__ == "__main__":
    main()
