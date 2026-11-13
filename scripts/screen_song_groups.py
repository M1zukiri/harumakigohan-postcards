# 2026/10/27 01:05:00 创建 —— 按“MV 规格足够 + 有足够分辨率图片”筛选可用歌曲组，输出可选曲表
import os, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
d = json.load(open(os.path.join(M, "postcard-index.json"), encoding="utf-8"))

MIN_KBPS = 700           # 视为“较高码率”的下限
MIN_RES = 1280 * 720     # 720P 及以上的像素数下限

def res_ok(res):
    w, h = map(int, res.lower().split("x"))
    return w * h >= MIN_RES

rows = []
for s in d["songs"]:
    mv_ok, mv_all = [], []
    for m in s["mv"]:
        for f in m["files"]:
            ok = res_ok(f["res"]) and f["kbps"] >= MIN_KBPS
            mv_all.append({"file": f["file"], "res": f["res"], "kbps": f["kbps"],
                           "dur": f["dur_s"], "ok": ok, "title": m["title"]})
            if ok:
                mv_ok.append(mv_all[-1])
    # 图片：该曲关联的 pixiv 作品中 A/B 级
    img_ok = []
    for p in s["pixiv"]:
        if p["grade"] in ("A", "B"):
            img_ok.append(p)
    rows.append({"song": s, "mv_ok": mv_ok, "mv_all": mv_all, "img_ok": img_ok})

usable = [r for r in rows if r["mv_ok"] and r["img_ok"]]
mv_only = [r for r in rows if r["mv_ok"] and not r["img_ok"]]
img_only = [r for r in rows if r["img_ok"] and not r["mv_ok"]]

print("可用（MV 合格 + 图片合格）：", len(usable))
for r in usable:
    s = r["song"]
    mv = max(r["mv_ok"], key=lambda x: x["kbps"])
    img = r["img_ok"][0]
    print("  %-30s | %s %s %dkbps | %s %s [%s]" % (
        s["title_ja"], mv["file"], mv["res"], mv["kbps"],
        img["title"][:18], img["size"], img["grade"]))

print("\n仅有合格 MV、无合格图片：", len(mv_only))
for r in mv_only:
    s = r["song"]
    mv = max(r["mv_ok"], key=lambda x: x["kbps"])
    print("  %-30s | %s %s %dkbps" % (s["title_ja"], mv["file"], mv["res"], mv["kbps"]))

print("\n仅有合格图片、无合格 MV：", len(img_only))
for r in img_only:
    s = r["song"]
    imgs = ", ".join("%s(%s,%s)" % (i["title"][:14], i["size"], i["grade"]) for i in r["img_ok"])
    print("  %-30s | %s" % (s["title_ja"], imgs))

json.dump({"usable": [{"song": r["song"]["id"], "title": r["song"]["title_ja"],
                       "date": r["song"]["release_date"],
                       "mv": r["mv_ok"], "img": r["img_ok"]} for r in usable],
           "mv_only": [{"song": r["song"]["id"], "title": r["song"]["title_ja"],
                        "mv": r["mv_ok"]} for r in mv_only],
           "img_only": [{"song": r["song"]["id"], "title": r["song"]["title_ja"],
                         "img": r["img_ok"]} for r in img_only]},
          open(os.path.join(M, "_song_groups.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> _song_groups.json")
