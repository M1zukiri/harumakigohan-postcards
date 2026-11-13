# 2026-10-26 23:18:09 创建
import os, json, sys
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
D = r"D:\Harumakigohan\image\custom"
rows = []
for f in sorted(os.listdir(D)):
    p = os.path.join(D, f)
    if not os.path.isfile(p):
        continue
    try:
        im = Image.open(p)
        w, h = im.size
        fmt = im.format
    except Exception as e:
        w = h = 0
        fmt = "ERR"
    rows.append({"file": f, "w": w, "h": h, "fmt": fmt,
                 "kb": round(os.path.getsize(p) / 1024, 1)})
rows.sort(key=lambda r: -(r["w"] * r["h"]))
print("总数:", len(rows))
from collections import Counter
print("格式:", dict(Counter(r["fmt"] for r in rows)))
print("分辨率 Top10:")
for r in rows[:10]:
    print("  {}x{} {} {:.0f}KB {}".format(r["w"], r["h"], r["fmt"], r["kb"], r["file"][:40]))
print("最小分辨率:", min(rows, key=lambda r: r["w"] * r["h"])["w"], "x", min(rows, key=lambda r: r["w"] * r["h"])["h"])
json.dump(rows, open(r"D:\Harumakigohan\manifest\image-custom-index.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
