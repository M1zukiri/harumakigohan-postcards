# 2026/10/27 03:30:00 创建 —— 用感知哈希把 custom 图片与 pixiv 已归档作品比对，找出重复与新增
import os, json, sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
DIMS = os.path.join(M, "image-dimensions.json")
OUT = os.path.join(M, "custom-vs-pixiv.json")


def dhash(path, size=16):
    with Image.open(path) as im:
        im = im.convert("L").resize((size + 1, size), Image.LANCZOS)
        px = list(im.getdata())
    bits = 0
    for r in range(size):
        row = px[r * (size + 1):(r + 1) * (size + 1)]
        for c in range(size):
            bits = (bits << 1) | (1 if row[c] > row[c + 1] else 0)
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


rows = json.load(open(DIMS, encoding="utf-8"))
pix = [r["file"] for r in rows if r["dir"] == "pixiv"]
cus = [r["file"] for r in rows if r["dir"] == "custom"]

ph = {}
for f in pix:
    p = os.path.join(ROOT, "image", "pixiv", f)
    try:
        ph[f] = dhash(p)
    except Exception as e:
        print("ERR pixiv", f, e)

out = []
for f in cus:
    p = os.path.join(ROOT, "image", "custom", f)
    try:
        h = dhash(p)
    except Exception as e:
        print("ERR custom", f, e)
        continue
    best, bestd = None, 999
    for pf, pv in ph.items():
        d = hamming(h, pv)
        if d < bestd:
            best, bestd = pf, d
    out.append({"file": f, "pixiv_match": best, "dist": bestd,
                "dup": bestd <= 8})

dups = [x for x in out if x["dup"]]
uni = [x for x in out if not x["dup"]]
print("custom 总数", len(out), "重复", len(dups), "独立", len(uni))
print("\n== 判定为重复 ==")
for x in sorted(dups, key=lambda x: x["dist"]):
    print("  %-55s ~ %-22s d=%d" % (x["file"][:55], x["pixiv_match"], x["dist"]))
print("\n== 独立图片（按与最近邻的距离）==")
for x in sorted(uni, key=lambda x: x["dist"]):
    print("  %-55s nearest=%-22s d=%d" % (x["file"][:55], x["pixiv_match"], x["dist"]))
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n->", OUT)
