# 2026/10/27 00:20:00 创建 —— 生成明信片素材索引（JSON + Markdown）
import os, json, re, sys
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
TW, TH = 1228, 1819
TR = TW / TH

cat = json.load(open(os.path.join(M, "catalog.json"), encoding="utf-8"))
works = {w["id"]: w for w in json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))}
dims = json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
fitness = {r["file"]: r for r in json.load(open(os.path.join(M, "_fitness.json"), encoding="utf-8"))}
custom_notes = json.load(open(os.path.join(M, "postcard-custom-notes.json"), encoding="utf-8"))
mv_files = json.load(open(os.path.join(M, "_mv_files.json"), encoding="utf-8"))

songs = [x for x in cat if x["type"] == "song"]
mvs = [x for x in cat if x["type"] == "mv"]

vinfo = {}
for line in open(os.path.join(M, "audit-report.md"), encoding="utf-8"):
    m = re.match(r"\|\s*(bili_BV\w+|yt_[\w-]+)\.mp4\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*(\d+x\d+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)s", line)
    if m:
        vinfo[m.group(1)] = {"file": m.group(1) + ".mp4", "res": m.group(4), "kbps": float(m.group(5)),
                             "dur_s": int(m.group(6)), "source": m.group(2)}

# 分类：非本家（他人 IP 二创 / 模写 / 他人作品）
NON_ORIGINAL = {
    "37666568", "38113150", "38385568", "38798225", "39559839", "39668470", "40260203",
    "45288803", "45719124", "48146697", "48865810", "49827495", "51387805", "55946746",
    "60084758", "61618895", "68030873", "68729191", "94760142",
}

# pixiv 作品 → 曲目（人工判定，依据写进 basis）
A2S = {
    "101881255": ("song-029", "曲绘 MeltyLandNightmare"),
    "67138070": ("song-029", "うごイラ，标签含曲名"),
    "66870841": ("song-023", "标签含曲名，Sunroom 场景"),
    "62811889": ("song-023", "标签含曲名"),
    "60595330": ("song-023", "标题 DREAMLESS，同名主题插画"),
    "67927199": ("song-030", "标题与标签均为曲名"),
    "89929372": ("song-051", "标题为曲名，本家"),
    "93936332": ("song-051", "うごイラ，标签含曲名"),
    "118778434": ("song-051", "みかげ生日贺图，标签含曲名"),
    "90713756": ("song-041", "标题 僕たちの約束"),
    "121941726": ("song-041", "The Promise 主题插画"),
    "123932226": ("song-041", "海辺の返信（B 站独家影像）"),
    "102116342": ("song-041", "龍使いの未練（B 站独家影像）"),
    "93037561": ("song-032", "标签セブンティーナ"),
    "81489931": ("song-032", "标签含 セブンティーナ/メルティ"),
    "84279741": ("song-046", "角色：ナナ・リリ"),
    "85116028": ("song-046", "角色：ナナ・リリ"),
    "106722823": ("song-066", "MV 分镜原图 11 页"),
    "112893547": ("song-069", "MV 分镜原图 11 页"),
    "121425440": ("song-069", "标签ゼロトーキング"),
    "139381641": ("song-069", "标签ゼロトーキング"),
    "119892154": ("song-071", "MV 分镜原图 13 页"),
    "125934990": ("song-071", "标签エンパープル"),
    "134968317": ("song-084", "MV 分镜原图 12 页"),
    "140354089": ("song-086", "MV 分镜原图 15 页"),
    "150568874": ("song-089", "MV 分镜原图 12 页"),
    "95435602": ("song-055", "MV 分镜原图 13 页"),
    "147038125": ("song-087", "标题为曲名"),
    "103086244": ("song-043", "角色群像，标签含 秘密/第三の心臓/彗星"),
}

# 独立素材（不归属单一曲目）
STANDALONE = {
    "140797559": "原创动画《お姉ちゃんごっこ》第一话分镜（23 页）",
    "150951404": "原创动画《お姉ちゃんごっこ》第二话分镜（35 页）",
    "91582734": "影像素材「わたしたちの未来は」（8 页，Nikon 相机企划）",
    "98979002": "幻影 LV 演唱会主视觉",
    "96375702": "角色设计：Mikage",
    "98047601": "角色漫画：みかげたちの漫画（3 页）",
    "100306718": "独立插画：小宇宙日和",
    "110733308": "独立插画：二番星を探しに",
    "114124948": "独立插画：夜汽車は走り出す",
    "118005856": "独立插画：夜見世",
    "91396435": "独立插画：舞灯会",
    "111352770": "独立插画：浮遊力（2 页）",
    "121211727": "独立插画：Selfie : Tokyo tower",
    "133361312": "独立插画：Relic",
    "103368035": "独立插画：静かな朝番",
    "104169529": "贺图：2023",
    "105226920": "贺图：九",
    "95244393": "贺图：2022（大集合）",
    "96211355": "贺图：8 周年",
    "100485024": "企划插画：ご当地幻影（4 页）",
    "79800088": "独立插画：はじまりの日",
    "81308705": "独立插画：晴れた日の心慮",
    "82270519": "独立插画：夜魔と探求",
    "83606408": "独立插画：それは知るということ",
    "87870639": "独立插画：八月三十一日",
    "87916995": "独立插画：藍のある星",
    "88933181": "独立插画：翠色衛星",
    "81056708": "独立插画：夜長のピクニック",
    "81873761": "独立插画：夜（4 页）",
    "77048087": "独立插画：こがね色の小惑星",
    "77059859": "独立插画：雪夜",
    "77309302": "独立插画：風のひとやすみ",
    "78880652": "独立插画：ともだち",
    "94939814": "独立插画：陽だまり",
    "108982505": "うごイラ：Want",
    "65590409": "うごイラ：金魚すくい",
    "66731817": "周边商品宣传图（托特包/马克杯）",
    "61522750": "独立插画：レインゴースト（疑似 Tender Rain 关联）",
    # 早期原创插画（2013–2016，与本目录曲目无直接归属）
    "38597282": "早期原创插画（2013）：文明の隙間",
    "39016910": "早期原创插画（2013）：ぱすてるとしょかん",
    "39176056": "早期原创插画（2013）：羽ついてる子ちゃん",
    "39377038": "早期原创插画（2013）：遠い街のテラスで",
    "40532425": "早期原创插画（2013）：テッシュ配り青サンタちゃん",
    "41445441": "早期原创插画（2014）：オレンジノイズ",
    "42261775": "早期原创插画（2014）：Mr.デスクライト",
    "43587930": "早期原创插画（2014）：ゆめ",
    "43728057": "早期原创插画（2014）：ギターガール",
    "44698873": "早期原创插画（2014）：Fender Mustang",
    "44890794": "早期原创插画（2014）：透明王女と雲と城（2 页）",
    "47495242": "早期原创插画（2014）：メロンソーダ系JK",
    "50313345": "早期原创插画（2015）：アイスちゃん",
    "50706447": "早期原创插画（2015）：Aerofoil",
    "53708344": "早期原创插画（2015）：少女はテレキャスターと夢を見る",
    "55222323": "早期原创插画（2016）：夜景の降る夜",
    "57539050": "早期原创插画（2016）：つぎでおりるね",
    "57756151": "早期原创插画（2016）：Into the Dark",
    "63675429": "早期原创插画（2017）：The Lost Century",
    "65190509": "早期原创插画（2017）：最後の花屋",
    "86765933": "贺图（2021）：賀正",
}


def fit(w, h):
    if w / h > TR:
        w2, h2 = h * TR, h
    else:
        w2, h2 = w, w / TR
    scale = max(TW / w2, TH / h2)
    keep = (w2 * h2) / (w * h)
    grade = "A" if scale <= 1.0 else "B" if scale <= 1.3 else "C" if scale <= 2.0 else "D"
    return int(w2), int(h2), round(scale, 3), round(keep, 3), grade


pixiv_pages = defaultdict(list)
for r in dims:
    if r["dir"] == "pixiv":
        pixiv_pages[r["file"].rsplit("_p", 1)[0]].append(r)

# ---- 组装曲目索引 ----
mv_by_song = defaultdict(list)
for mv in mvs:
    base = re.sub(r"（.*?）", "", mv["title_ja"])
    base = re.sub(r"\s*\(.*?\)", "", base).strip()
    for s in songs:
        for cand in (s["title_ja"], s["title_zh"]):
            if not cand:
                continue
            if cand == base or (len(cand) >= 4 and (cand in mv["title_ja"])):
                mv_by_song[s["id"]].append(mv["id"])
                break
        else:
            continue
        break

out = {"meta": {"generated": "2026-10-27", "target_px": [TW, TH],
                "target_cm": "10×15cm @300ppi",
                "sources": ["catalog.json", "pixiv-works.json", "image-dimensions.json",
                            "audit-report.md", "postcard-custom-notes.json"]},
       "songs": [], "front_pool": [], "element_pool": [], "standalone": [],
       "non_original": [], "gaps": []}

front_pool, element_pool = [], []

for s in songs:
    entry = {"id": s["id"], "title_ja": s["title_ja"], "title_zh": s["title_zh"],
             "release_date": s["release_date"], "mv": [], "pixiv": [], "front": [], "notes": []}
    for mvid in mv_by_song.get(s["id"], []):
        mv = next(m for m in mvs if m["id"] == mvid)
        files = [{"key": k, **vinfo[k]} for k in mv_files.get(mvid, []) if k in vinfo]
        entry["mv"].append({"id": mvid, "title": mv["title_ja"], "type": mv["mv_type_zh"],
                            "files": files})
        if not files:
            entry["notes"].append("MV 条目存在但本地无影音文件")
    if s["id"] in {v[0] for v in A2S.values()}:
        pass
    for pid, (sid, basis) in A2S.items():
        if sid != s["id"]:
            continue
        pages = pixiv_pages.get(pid, [])
        if not pages:
            continue
        w0, h0 = pages[0]["w"], pages[0]["h"]
        cw, ch, scale, keep, grade = fit(w0, h0)
        rec = {"id": pid, "title": works[pid]["title"], "date": works[pid]["createDate"][:10],
               "pages": len(pages), "size": "%dx%d" % (w0, h0), "basis": basis,
               "grade": grade, "scale": scale, "keep": keep,
               "files": [p["file"] for p in pages]}
        entry["pixiv"].append(rec)
        if grade == "A" and pid not in {x["pixiv"] for x in front_pool}:
            front_pool.append({"file": pages[0]["file"], "pixiv": pid, "title": works[pid]["title"],
                               "song": s["id"], "song_title": s["title_ja"], "size": "%dx%d" % (w0, h0),
                               "grade": grade, "scale": scale, "keep": keep,
                               "cut": "%dx%d" % (cw, ch), "pages": len(pages)})
        if len(pages) >= 3:
            element_pool.append({"source": "pixiv 分镜组", "pixiv": pid,
                                 "title": works[pid]["title"], "song": s["id"],
                                 "song_title": s["title_ja"], "count": len(pages),
                                 "size": "1920x1080", "files": [p["file"] for p in pages]})
    if entry["mv"] or entry["pixiv"]:
        pass
    out["songs"].append(entry)

# 独立素材池
for pid, note in STANDALONE.items():
    pages = pixiv_pages.get(pid, [])
    if not pages:
        continue
    w0, h0 = pages[0]["w"], pages[0]["h"]
    cw, ch, scale, keep, grade = fit(w0, h0)
    rec = {"id": pid, "title": works[pid]["title"], "date": works[pid]["createDate"][:10],
           "pages": len(pages), "size": "%dx%d" % (w0, h0), "note": note,
           "grade": grade, "scale": scale, "keep": keep,
           "files": [p["file"] for p in pages]}
    out["standalone"].append(rec)
    if grade == "A" and pid not in {x["pixiv"] for x in front_pool}:
        front_pool.append({"file": pages[0]["file"], "pixiv": pid, "title": works[pid]["title"],
                           "song": None, "song_title": note,
                           "size": "%dx%d" % (w0, h0), "grade": grade, "scale": scale,
                           "keep": keep, "cut": "%dx%d" % (cw, ch), "pages": len(pages)})
    if len(pages) >= 3:
        element_pool.append({"source": "pixiv 分镜组", "pixiv": pid, "title": works[pid]["title"],
                             "song": None, "song_title": note, "count": len(pages),
                             "size": "1920x1080", "files": [p["file"] for p in pages]})

# MV 视频作为元素来源
for s in songs:
    for m in next(x for x in out["songs"] if x["id"] == s["id"])["mv"]:
        if m["files"]:
            element_pool.append({"source": "MV 视频", "song": s["id"], "song_title": s["title_ja"],
                                 "mv": m["id"], "mv_title": m["title"], "count": len(m["files"]),
                                 "size": m["files"][0]["res"], "files": [f["file"] for f in m["files"]]})

# 非本家作品
for pid in sorted(NON_ORIGINAL):
    if pid in works:
        pages = pixiv_pages.get(pid, [])
        out["non_original"].append({"id": pid, "title": works[pid]["title"],
                                    "date": works[pid]["createDate"][:10],
                                    "tags": works[pid]["tags"][:3],
                                    "files": [p["file"] for p in pages]})

out["front_pool"] = sorted(front_pool, key=lambda x: (x["grade"], -max(
    [int(v) for v in x["size"].split("x")])))
out["element_pool"] = element_pool

# custom 图片汇总（含正面评级）
custom_rows = []
for r in dims:
    if r["dir"] != "custom":
        continue
    cw, ch, scale, keep, grade = fit(r["w"], r["h"])
    note = custom_notes.get(r["file"], {"desc": "", "src": ""})
    custom_rows.append({"file": r["file"], "size": "%dx%d" % (r["w"], r["h"]), "grade": grade,
                        "scale": scale, "keep": keep, "desc": note.get("desc", ""),
                        "src": note.get("src", "")})
out["custom"] = custom_rows

json.dump(out, open(os.path.join(M, "postcard-index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

covered = set(A2S) | set(STANDALONE) | NON_ORIGINAL
missing_cover = [p for p in works if p not in covered]
print("作品覆盖校验：未归类", missing_cover)
print("songs", len(out["songs"]), "front", len(front_pool), "elements", len(element_pool),
      "standalone", len(out["standalone"]), "non-original", len(out["non_original"]))
print("曲目有素材:", sum(1 for s in out["songs"] if s["mv"] or s["pixiv"]))
print("-> postcard-index.json")
