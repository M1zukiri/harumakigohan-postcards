# 2026/10/26 23:30:00 创建 —— 测量 image/ 下全部图片像素尺寸与宽高比
import os, json, sys
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\Harumakigohan"
IMG = os.path.join(ROOT, "image")
OUT = os.path.join(ROOT, "manifest", "image-dimensions.json")

# 明信片正面官方规格：1228 x 1819 px @300ppi（10x15cm 级）
TARGET_W, TARGET_H = 1228, 1819


def scan(folder):
    rows = []
    for name in sorted(os.listdir(folder)):
        p = os.path.join(folder, name)
        if not os.path.isfile(p):
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
                fmt = im.format
                mode = im.mode
        except Exception as e:
            rows.append({"file": name, "dir": os.path.basename(folder),
                         "error": str(e)[:120]})
            continue
        rows.append({
            "file": name,
            "dir": os.path.basename(folder),
            "w": w, "h": h, "format": fmt, "mode": mode,
            "bytes": os.path.getsize(p),
            "ratio": round(w / h, 4),
        })
    return rows


rows = []
for sub in ("pixiv", "custom"):
    d = os.path.join(IMG, sub)
    if os.path.isdir(d):
        rows.extend(scan(d))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

ok = [r for r in rows if "w" in r]
print("total", len(rows), "ok", len(ok), "err", len(rows) - len(ok))
print("w x h 分布（前 15）:")
from collections import Counter
c = Counter((r["w"], r["h"]) for r in ok)
for (w, h), n in c.most_common(15):
    print("  %5d x %5d  %3d  比值 %.3f" % (w, h, n, w / h))
print("\n满足 1228x1819（竖版：h>=1819 且 w>=1228）:", sum(1 for r in ok if r["h"] >= 1819 and r["w"] >= 1228))
print("旋转后满足（横版：w>=1819 且 h>=1228）:", sum(1 for r in ok if r["w"] >= 1819 and r["h"] >= 1228))
print("竖版比例在 0.60-0.75 之间的（接近明信片 0.675）:", sum(1 for r in ok if 0.60 <= r["ratio"] <= 0.75))
print("完全等于 1228x1819 的:", sum(1 for r in ok if r["w"] == 1228 and r["h"] == 1819))
print("写入", OUT)
