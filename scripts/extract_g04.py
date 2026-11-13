# 2026-10-28 19:40:00 G04-G07 组贴纸提取。先跑 MangaLine 基线，再按图类型补外轮廓
import os
import sys
import json
import glob

import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
GROUP = "G04-G07_コバルトメモリーズ_セブンティーナ"
DST = os.path.join(ROOT, "postcards", "_workbench", "stickers", GROUP)
REV = os.path.join(ROOT, "postcards", "_workbench", "out", "review_g04")

from extract_f2 import save_rgba, contour_alpha, preview  # noqa: E402
from extract_f3 import mle_line, load_any  # noqa: E402


def crop_from_job(tid):
    j = json.load(open(os.path.join(TASKS, tid + ".json"), encoding="utf-8"))
    im = Image.open(os.path.join(TASKS, j["image_file"])).convert("RGB")
    r = j.get("rect")
    if r:
        x, y = max(r["x"], 0), max(r["y"], 0)
        im = im.crop((x, y, min(x + r["w"], im.width), min(y + r["h"], im.height)))
    return j, im


def run(tid, name, fn, scale=1.4, tag="_base_"):
    j, im = crop_from_job(tid)
    roi = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    a = fn(roi) * 255.0
    p = os.path.join(REV, tag + tid + ".png")
    save_rgba(p, a, scale, soft=True)
    print("%s %-22s %-16s rgb=%s max=%.0f mean=%.1f" % (
        tid, name, str(im.size), str(j.get("desc", ""))[:10], a.max(), a.mean()))


JOBS = [
    ("T20261028_190853", "人物_电台", 1),
    ("T20261028_190908", "草帽", 1),
    ("T20261028_190921", "人物_背影", 1),
    ("T20261028_190930", "人物_草帽侧身", 1),
    ("T20261028_190938", "人物_特写脸", 1),
    ("T20261028_190956", "双人_吉他", 1),
    ("T20261028_191004", "人物_微笑特写", 1),
    ("T20261028_191020", "鸽子", 1),
    ("T20261028_191030", "鸽子_屋顶", 1),
    ("T20261028_191042", "蝴蝶结", 1),
    ("T20261028_191052", "手机", 1),
    ("T20261028_191102", "罐头", 1),
    ("T20261028_191111", "路牌", 1),
    ("T20261028_191133", "演出票", 1),
    ("T20261028_191149", "字迹_Seventina", 1),
    ("T20261028_191201", "时钟", 1),
    ("T20261028_191212", "闹钟", 1),
    ("T20261028_191223", "窗户", 1),
    ("T20261028_191238", "前景_窗前", 1),
]


if __name__ == "__main__":
    os.makedirs(REV, exist_ok=True)
    os.makedirs(DST, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "base"
    for tid, name, _ in JOBS:
        if mode == "base":
            run(tid, name, lambda r: mle_line(r))
        else:
            run(tid, name, lambda r: mle_line(r, clahe=True), tag="_clahe_")
