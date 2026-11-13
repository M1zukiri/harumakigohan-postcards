# 2026/10/26 23:45:00 创建 —— 汇总曲目、MV、视频文件、pixiv 作品，生成明信片素材索引底稿
import os, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")

cat = json.load(open(os.path.join(M, "catalog.json"), encoding="utf-8"))
works = json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))
dims = json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))

songs = [x for x in cat if x["type"] == "song"]
mvs = [x for x in cat if x["type"] == "mv"]
albums = [x for x in cat if x["type"] == "album"]

# ---- 视频文件清单（来自 audit-report 明细表）----
video_files = {}
for line in open(os.path.join(M, "audit-report.md"), encoding="utf-8"):
    m = re.match(r"\|\s*(bili_BV\w+|yt_[\w-]+)\.mp4\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*(\d+x\d+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)s", line)
    if m:
        video_files[m.group(1)] = {
            "file": m.group(1) + ".mp4", "source": m.group(2),
            "mb": float(m.group(3)), "res": m.group(4),
            "kbps": float(m.group(5)), "dur_s": int(m.group(6)),
        }

# ---- 视频标题（来自 video-index.md）----
video_titles = {}
for line in open(os.path.join(M, "video-index.md"), encoding="utf-8"):
    m = re.match(r"\|\s*(bili_BV\w+|yt_[\w-]+)\.mp4\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|", line)
    if m:
        video_titles[m.group(1)] = {"platform": m.group(2), "title": m.group(3).strip()}


def vidkey(url):
    """从官方链接里取出与文件名对应的键"""
    m = re.search(r"bilibili\.com/video/(BV\w+)", url)
    if m:
        return "bili_" + m.group(1)
    m = re.search(r"[?&]v=([\w-]{6,})", url)
    if m:
        return "yt_" + m.group(1)
    return None


# MV 条目的 id → 本地视频文件
mv_to_files = {}
for mv in mvs:
    keys = []
    for p in mv.get("platforms") or []:
        k = vidkey(p.get("url") or "")
        if k:
            keys.append(k)
    mv_to_files[mv["id"]] = [k for k in keys if k in video_files]

# ---- pixiv 作品尺寸汇总 ----
pw = {}
for r in dims:
    if r["dir"] != "pixiv":
        continue
    pid = r["file"].rsplit("_p", 1)[0]
    pw.setdefault(pid, []).append((r["w"], r["h"], r["file"]))

# ---- 曲目 ↔ pixiv 作品：标题/标签关键词匹配 ----
def norm(s):
    return re.sub(r"[\s　\-–—_:：·・!！?？'\"“”‘’()（）\[\]【】]", "", (s or "")).lower()


title_map = {}  # pixiv pid -> song id
for w in works:
    nt = norm(w["title"])
    tagset = {norm(t) for t in w["tags"]}
    if not nt:
        continue
    for s in songs:
        for cand in (s["title_ja"], s["title_zh"]):
            nc = norm(cand)
            if nc and (nc == nt or (len(nc) >= 3 and nc in nt) or (len(nt) >= 3 and nt in nc)):
                title_map[w["id"]] = s["id"]
                break
        if w["id"] in title_map:
            break
    if w["id"] not in title_map:
        for s in songs:
            for cand in (s["title_ja"], s["title_zh"]):
                if norm(cand) and norm(cand) in tagset:
                    title_map[w["id"]] = s["id"]
                    break
            if w["id"] in title_map:
                break

# ---- 输出统计 ----
print("songs", len(songs), "mvs", len(mvs), "albums", len(albums))
print("视频文件", len(video_files), "MV 条目", len(mvs))
linked = {k: v for k, v in mv_to_files.items() if v}
print("MV 已匹配本地文件:", len(linked), "/", len(mvs))
nolink = [(mv["id"], mv["title_ja"], [p["url"] for p in mv["platforms"]]) for mv in mvs if not mv_to_files[mv["id"]]]
print("\nMV 未匹配本地文件:")
for x in nolink:
    print("  ", x[0], x[1], x[2][:2])

print("\n== 本地视频文件未被任何 MV 条目引用 ==")
used = {f for v in mv_to_files.values() for f in v}
for k in sorted(video_files):
    if k not in used:
        print("  ", k, video_titles.get(k, {}).get("title", "")[:60])

print("\n== pixiv 作品标题匹配到曲目 ==")
for pid, sid in sorted(title_map.items()):
    s = next(x for x in songs if x["id"] == sid)
    w = next(x for x in works if x["id"] == pid)
    print("  %s %-28s -> %s %s" % (pid, w["title"][:28], sid, s["title_ja"]))

json.dump({"video_files": video_files, "video_titles": video_titles,
           "mv_to_files": mv_to_files, "pixiv_title_map": title_map},
          open(os.path.join(M, "_draft_links.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> _draft_links.json")
