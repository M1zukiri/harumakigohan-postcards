# 2026/10/27 02:10:00 创建 —— 全量列出有合格 MV 的曲目（25 首），缺合格插画者加备注
import os, json, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
idx = json.load(open(os.path.join(M, "postcard-index.json"), encoding="utf-8"))
works = {w["id"]: w for w in json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))}
dims = json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
MIN_KBPS, MIN_RES = 700, 1280 * 720
TW, TH = 1228, 1819

EXTRA = {
    "song-024": [("93037561", "标签含 コバルトメモリーズ，与 セブンティーナ 共用")],
    "song-044": [("103086244", "标签含 彗星になれたなら，与 秘密 共用")],
    "song-056": [("98979002", "同名演唱会主视觉「幻影LV」")],
    "song-063": [("96375702", "本曲主角角色设计图 Mikage")],
    "song-051": [("103086244", "角色群像，标签含 第三の心臓")],
}
TAG = {"song-023": "曲绘", "song-024": "概念图", "song-032": "概念图", "song-041": "曲绘",
       "song-043": "角色群像", "song-044": "角色群像", "song-051": "曲绘", "song-056": "主视觉",
       "song-063": "角色设计", "song-069": "曲绘", "song-071": "贺图"}
NOTE = {
    "song-023": "MV 取 Acoustic「Nightwalker」版（1542kbps）；原版 MV 为 yt 720p 689kbps。",
    "song-024": "「昼下」为横构图概念图，裁竖版保留 31%，构图需重排。",
    "song-032": "「昼下」与 コバルトメモリーズ 共用。",
    "song-041": "「海辺の返信」「龍使いの未練」是同世界观独家影像，非本曲曲绘。",
    "song-043": "「リリナナみかげ」与 彗星になれたなら 共用。",
    "song-044": "「リリナナみかげ」与 秘密 共用。",
    "song-051": "「第三の心臓」「みかげの誕生日」为直系曲绘。",
    "song-056": "「幻影LV」是演唱会主视觉，非曲绘。",
    "song-063": "「Mikage」是白底角色设计图；MV 码率 786kbps 为组内最低。",
    "song-069": "「Afternoon」「小さなキャラバン」均为直系曲绘。",
    "song-071": "「2025」为新年贺图。",
}

pixiv_pages = {}
for r in dims:
    if r["dir"] == "pixiv":
        pixiv_pages.setdefault(r["file"].rsplit("_p", 1)[0], []).append(r)


def fit(w, h):
    r = w / h
    if r > TW / TH:
        w2, h2 = h * TW / TH, h
    else:
        w2, h2 = w, w / (TW / TH)
    scale = max(TW / w2, TH / h2)
    keep = (w2 * h2) / (w * h)
    g = "A" if scale <= 1.0 else "B" if scale <= 1.3 else "C" if scale <= 2.0 else "D"
    return int(w2), int(h2), round(scale, 3), round(keep, 3), g


def res_ok(res):
    w, h = map(int, res.lower().split("x"))
    return w * h >= MIN_RES


rows = []
for s in idx["songs"]:
    mv_ok = []
    for m in s["mv"]:
        for f in m["files"]:
            if res_ok(f["res"]) and f["kbps"] >= MIN_KBPS:
                mv_ok.append({**f, "mv_title": m["title"]})
    if not mv_ok:
        continue                      # 一票否决：无合格 MV 不进表
    imgs = []
    for p in s["pixiv"]:
        if p["grade"] == "A":
            imgs.append({"pid": p["id"], "title": p["title"], "size": p["size"],
                         "grade": p["grade"], "pages": p["pages"], "file": p["files"][0],
                         "keep": p.get("keep", 0)})
    for pid, why in EXTRA.get(s["id"], []):
        pages = pixiv_pages.get(pid, [])
        if not pages:
            continue
        cw, ch, scale, keep, g = fit(pages[0]["w"], pages[0]["h"])
        if g == "A" and pid not in {i["pid"] for i in imgs}:
            imgs.append({"pid": pid, "title": works[pid]["title"],
                         "size": "%dx%d" % (pages[0]["w"], pages[0]["h"]), "grade": g,
                         "pages": len(pages), "file": pages[0]["file"], "keep": keep})
    # 已有的不合规格图，用于写备注（分镜组已在背面元素列说明，不重复）
    big_multipage = [p for p in s["pixiv"] if p["pages"] >= 3]
    mp_ids = {p["id"] for p in big_multipage}
    weak = []
    for p in s["pixiv"]:
        if p["grade"] != "A" and p["id"] not in mp_ids:
            weak.append("%s（%s，需放大 %.1f×，仅够背面元素）" % (p["title"], p["size"], p["scale"]))
    mv_ok.sort(key=lambda x: -x["kbps"])
    rows.append({"song": s, "mv": mv_ok, "img": imgs, "weak": weak,
                 "multipage": big_multipage})

rows.sort(key=lambda r: r["song"]["release_date"])


def gap_note(r):
    if r["img"]:
        return NOTE.get(r["song"]["id"], "")
    bits = ["**缺合格插画**，pixiv 本账号 107 作品中无该曲作品，需另找"]
    if r["multipage"]:
        bits.append("现有 %d 页 1920×1080 分镜原图可作背面元素" % r["multipage"][0]["pages"])
    if r["weak"]:
        bits.append("；".join(r["weak"][:2]))
    return "；".join(bits)


L = []
A = L.append
A("# 有合格 MV 的曲目与素材组")
A("")
A("筛选条件：MV 分辨率 ≥720P 且视频码率 ≥%d kbps。**无合格 MV 的曲目一票否决，不在此表。**" % MIN_KBPS)
A("")
A("正面图片要求：关联插画为 A 档——裁成 1228×1819 后无需插值放大。")
A("")
A("共 **%d 首**：%d 首有 A 档插画，%d 首缺 A 档插画（可另行补源）。" % (
    len(rows), sum(1 for r in rows if r["img"]), sum(1 for r in rows if not r["img"])))
A("")
A("| 歌曲名 | 组号 | 发行日 | MV 影音（码率） | 正面图片候选 | 背面元素 | 备注 | 选 |")
A("|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows, 1):
    s = r["song"]
    gid = "G%02d" % i
    mv = r["mv"][0]
    mvtxt = "`%s` %s %dkbps" % (mv["file"], mv["res"], mv["kbps"])
    if len(r["mv"]) > 1:
        mvtxt += "<br>（另有 %d 条）" % (len(r["mv"]) - 1)
    if r["img"]:
        tag = TAG.get(s["id"], "")
        imgtxt = "<br>".join("%s %s（保留 %.0f%%）%s" % (
            im["title"], im["size"], im["keep"] * 100, "（%s）" % tag if tag else "")
            for im in r["img"])
    else:
        imgtxt = "—"
    eltxt = "MV 截帧"
    if r["multipage"]:
        eltxt += " + 分镜组 %d 页" % r["multipage"][0]["pages"]
    A("| %s | %s | %s | %s | %s | %s | %s |  |" % (
        s["title_ja"], gid, s["release_date"], mvtxt, imgtxt, eltxt, gap_note(r)))
A("")
A("## 备注说明")
A("")
A("- 缺 A 档插画的 %d 首，pixiv 本账号 107 个作品已逐个核对，确实没有对应作品；补源可考虑 X（@harumaki_gohan）、官博、周边与 Blu-ray 小册子扫描。" % sum(1 for r in rows if not r["img"]))
A("- 多首曲目共用同一张插画的情况已在备注标明，实际每组只能用一次。")
A("- 背面元素：MV 截帧适用于全部曲目；标注「分镜组」的曲目另有 1920×1080 逐页原图，抠元素质量更高。")
A("")

open(os.path.join(M, "postcard-song-groups.md"), "w", encoding="utf-8").write("\n".join(L))
json.dump([{"group": "G%02d" % (i + 1), "song_id": r["song"]["id"], "title": r["song"]["title_ja"],
            "date": r["song"]["release_date"], "status": "ready" if r["img"] else "need-illust",
            "mv": r["mv"], "img": r["img"], "note": gap_note(r)}
           for i, r in enumerate(rows)],
          open(os.path.join(M, "postcard-song-groups.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("rows", len(rows), "ready", sum(1 for r in rows if r["img"]), "need", sum(1 for r in rows if not r["img"]))
for i, r in enumerate(rows, 1):
    print("G%02d %-26s %-10s %s | %s" % (i, r["song"]["title_ja"], r["song"]["release_date"],
                                         "有图" if r["img"] else "缺图",
                                         ",".join(im["title"][:14] for im in r["img"]) or "-"))
