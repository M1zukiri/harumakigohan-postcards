# 2026/10/27 00:05:00 创建 —— 生成明信片素材索引（曲目↔MV↔pixiv↔custom），含正面可用性评级
import os, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")

TARGET_W, TARGET_H = 1228, 1819
TARGET_R = TARGET_W / TARGET_H  # 0.67509

cat = json.load(open(os.path.join(M, "catalog.json"), encoding="utf-8"))
works = {w["id"]: w for w in json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))}
dims = json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
custom_notes = json.load(open(os.path.join(M, "postcard-custom-notes.json"), encoding="utf-8"))

songs = [x for x in cat if x["type"] == "song"]
mvs = [x for x in cat if x["type"] == "mv"]

# ---------- 视频文件与 MV 映射（手工校正后用 _mv_files.json） ----------
mv_files = json.load(open(os.path.join(M, "_mv_files.json"), encoding="utf-8"))
# 校正：Live 三曲合辑不应挂到 mv-035 单曲；Mirage / Dinner Bell 的本家演唱版补配
if "bili_BV1SDpuzUEa9" in mv_files.get("mv-035", []):
    mv_files["mv-035"].remove("bili_BV1SDpuzUEa9")
if "yt_LIoHb_oKIxI" not in mv_files.get("mv-044", []):
    mv_files.setdefault("mv-044", []).append("yt_LIoHb_oKIxI")
if "yt_sqW-nJhXbok" not in mv_files.get("mv-048", []):
    mv_files.setdefault("mv-048", []).append("yt_sqW-nJhXbok")

vinfo = {}
for line in open(os.path.join(M, "audit-report.md"), encoding="utf-8"):
    m = re.match(r"\|\s*(bili_BV\w+|yt_[\w-]+)\.mp4\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*(\d+x\d+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)s", line)
    if m:
        vinfo[m.group(1)] = {"file": m.group(1) + ".mp4", "res": m.group(4),
                             "kbps": float(m.group(5)), "dur_s": int(m.group(6)),
                             "source": m.group(2)}
vtitle = {}
for line in open(os.path.join(M, "video-index.md"), encoding="utf-8"):
    m = re.match(r"\|\s*(bili_BV\w+|yt_[\w-]+)\.mp4\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|", line)
    if m:
        vtitle[m.group(1)] = {"platform": m.group(2), "title": m.group(3).strip()}

# ---------- 图片池 ----------
P = {}
for r in dims:
    P.setdefault(r["file"], dict(r))

pixiv_pages = {}
for r in dims:
    if r["dir"] == "pixiv":
        pixiv_pages.setdefault(r["file"].rsplit("_p", 1)[0], []).append(r)


def fit(w, h):
    """按目标 1228x1819 竖版裁切，返回裁后像素、放大倍数、面积保留率"""
    if w / h > TARGET_R:            # 太宽：以高度为准，裁两侧
        w2, h2 = h * TARGET_R, h
    else:                            # 太窄：以宽度为准，裁上下
        w2, h2 = w, w / TARGET_R
    scale = max(TARGET_W / w2, TARGET_H / h2)
    keep = (w2 * h2) / (w * h)
    if scale <= 1.0:
        grade = "A"
    elif scale <= 1.3:
        grade = "B"
    elif scale <= 2.0:
        grade = "C"
    else:
        grade = "D"
    return {"cut_w": int(w2), "cut_h": int(h2), "scale": round(scale, 3),
            "keep": round(keep, 3), "grade": grade}


# ---------- pixiv 作品 → 曲目（人工校正表；依据写入 basis） ----------
MANUAL = {
    # pid: (song_id 或 None, basis)
    "101881255": ("song-029", "曲绘：MeltyLandNightmare"),
    "67138070": ("song-029", "标签含 メルティランドナイトメア（うごイラ）"),
    "66870841": ("song-023", "标签含 ドリームレス・ドリームス"),
    "62811889": ("song-023", "标签含 ドリームレス・ドリームス"),
    "60595330": ("song-023", "标题/标签 DREAMLESS"),
    "61522750": ("song-013", "标签雨 + 2017 年插画，疑似 Tender Rain 关联"),
    "67927199": ("song-030", "标题与标签均为 地球をあげる"),
    "89929372": ("song-051", "标题第三の心臓"),
    "93936332": ("song-051", "标签第三の心臓"),
    "118778434": ("song-051", "标题みかげの誕生日，标签第三の心臓"),
    "90713756": ("song-041", "标题僕たちの約束"),
    "93037561": ("song-032", "标签セブンティーナ/コバルトメモリーズ"),
    "81489931": ("song-032", "标签メルティランドナイトメア/セブンティーナ"),
    "84279741": ("song-046", "标题ナナ＆リリ（角色）"),
    "85116028": ("song-046", "标题ナナ×3 & リリ×2（角色）"),
    "106722823": ("song-066", "MV 分镜原图：ディナーベル"),
    "112893547": ("song-069", "MV 分镜原图：ゼロトーキング"),
    "119892154": ("song-071", "MV 分镜原图：エンパープル"),
    "134968317": ("song-084", "MV 分镜原图：アタマモミ"),
    "140354089": ("song-086", "MV 分镜原图：ドッペルゲンガー"),
    "150568874": ("song-089", "MV 分镜原图：マイバッド"),
    "95435602": ("song-055", "MV 分镜原图：蛍はいなかった"),
    "140797559": (None, "原创动画《お姉ちゃんごっこ》第一话分镜"),
    "150951404": (None, "原创动画《お姉ちゃんごっこ》第二话分镜"),
    "91582734": (None, "「わたしたちの未来は」影像素材（8 页）"),
    "98979002": (None, "幻影 LV 演唱会主视觉"),
    "100306718": (None, "独立插画：小宇宙日和"),
    "110733308": (None, "独立插画：二番星を探しに"),
    "114124948": (None, "独立插画：夜汽車は走り出す"),
    "118005856": (None, "独立插画：夜見世"),
    "91396435": (None, "独立插画：舞灯会"),
    "111352770": (None, "独立插画：浮遊力"),
    "121211727": (None, "独立插画：Selfie : Tokyo tower"),
    "133361312": (None, "独立插画：Relic"),
    "103368035": (None, "独立插画：静かな朝番（メイド）"),
    "96375702": (None, "角色设计：Mikage"),
    "98047601": (None, "角色漫画：みかげたちの漫画"),
    "103086244": (None, "角色群像：リリナナみかげ"),
    "104169529": (None, "贺图：2023"),
    "105226920": (None, "贺图：九"),
    "95244393": (None, "贺图：2022"),
    "96211355": (None, "贺图：8 周年"),
    "125934990": ("song-071", "标签エンパープル"),
    "121425440": ("song-069", "标签ゼロトーキング"),
    "139381641": ("song-069", "标签ゼロトーキング"),
    "121941726": ("song-041", "标签草原，对应 The Promise/約束"),
    "123932226": ("song-041", "标题海辺の返信（B 站独家影像）"),
    "102116342": ("song-041", "标题龍使いの未練（B 站独家影像）"),
    "147038125": ("song-087", "标题おでこテレパス"),
    "79800088": (None, "独立插画：はじまりの日"),
    "81308705": (None, "独立插画：晴れた日の心慮"),
    "82270519": (None, "独立插画：夜魔と探求"),
    "83606408": (None, "独立插画：それは知るということ"),
    "87870639": (None, "独立插画：八月三十一日"),
    "87916995": (None, "独立插画：藍のある星"),
    "88933181": (None, "独立插画：翠色衛星"),
    "94760142": (None, "他社曲插图：きゅうくらりん"),
    "81056708": (None, "独立插画：夜長のピクニック"),
    "45191000": (None, "unknown"),
}

auto = json.load(open(os.path.join(M, "_draft_links.json"), encoding="utf-8"))["pixiv_title_map"]

song_assets = {s["id"]: {"pixiv": [], "mv": []} for s in songs}
unassigned = []
for pid, w in works.items():
    song, basis = MANUAL.get(pid, (None, None))
    if pid in auto and song is None:
        song, basis = auto[pid], "标题匹配"
    if song and song in song_assets:
        song_assets[song]["pixiv"].append((pid, basis))
    else:
        unassigned.append((pid, basis or "未归类"))

# ---------- 输出摘要 ----------
rows = []
for r in dims:
    f = fit(r["w"], r["h"])
    rows.append({**r, **f})
rows.sort(key=lambda x: (x["grade"], x["scale"], -x["w"] * x["h"]))

print("图片总数", len(rows))
from collections import Counter
print("正面评级", Counter(r["grade"] for r in rows))
print("\nA 级（无需放大即可出 1228x1819）:")
for r in rows:
    if r["grade"] == "A":
        print("  %s  %4dx%-4d 裁后 %dx%d scale=%.2f 保留%.0f%%" %
              (r["file"], r["w"], r["h"], r["cut_w"], r["cut_h"], r["scale"], r["keep"] * 100))
print("\nB 级（轻放大 ≤1.3）：")
for r in rows:
    if r["grade"] == "B":
        print("  %s  %4dx%-4d scale=%.2f" % (r["file"], r["w"], r["h"], r["scale"]))
print("\n未归类 pixiv 作品数:", len(unassigned))
json.dump(rows, open(os.path.join(M, "_fitness.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("-> _fitness.json")
