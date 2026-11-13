# 2026/10/26 23:52:00 创建 —— 完善 MV/视频/pixiv 关联，输出核对表
import os, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
D = json.load(open(os.path.join(M, "_draft_links.json"), encoding="utf-8"))
cat = json.load(open(os.path.join(M, "catalog.json"), encoding="utf-8"))
works = {w["id"]: w for w in json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))}

video_files, video_titles = D["video_files"], D["video_titles"]
mvs = [x for x in cat if x["type"] == "mv"]


def norm(s):
    s = (s or "").lower()
    return re.sub(r"[\s　\-–—_:：·・!！?？'\"“”‘’()（）\[\]【】/／,，.。]", "", s)


used = {}
for mv in mvs:
    keys = []
    for p in mv.get("platforms") or []:
        u = p.get("url") or ""
        m = re.search(r"bilibili\.com/video/(BV\w+)", u)
        if m and ("bili_" + m.group(1)) in video_files:
            keys.append("bili_" + m.group(1))
        m = re.search(r"[?&]v=([\w-]{6,})", u)
        if m and ("yt_" + m.group(1)) in video_files:
            keys.append("yt_" + m.group(1))
    used[mv["id"]] = keys

assigned = {k for v in used.values() for k in v}
rest = [k for k in video_files if k not in assigned]

# 对剩余视频，用标题相似度匹配 MV 条目
for k in rest:
    vt = norm(video_titles.get(k, {}).get("title", ""))
    if not vt:
        continue
    best, score = None, 0.0
    for mv in mvs:
        for cand in (mv["title_ja"], mv.get("title_zh") or ""):
            nc = norm(cand)
            if len(nc) < 4:
                continue
            # 取较短者为子串长度度量
            common = 0
            for i in range(0, len(nc) - 3):
                if nc[i:i + 4] in vt:
                    common = max(common, 4)
            if nc in vt:
                common = len(nc)
            if common > score:
                best, score = mv["id"], common
    if best and score >= 4:
        used[best].append(k)
        print("标题补配:", k, "->", best, "|", video_titles[k]["title"][:50])

print("\n== MV -> 本地视频 ==")
for mv in mvs:
    print("%s %-40s %s" % (mv["id"], mv["title_ja"][:40], ", ".join(used[mv["id"]]) or "-"))

left = [k for k in video_files if k not in {x for v in used.values() for x in v}]
print("\n== 仍未归属的本地视频（%d）==" % len(left))
for k in left:
    print("  ", k, video_files[k]["res"], video_titles.get(k, {}).get("title", "")[:70])

json.dump(used, open(os.path.join(M, "_mv_files.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# pixiv 作品分类报表
dims = json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
pg = {}
for r in dims:
    if r["dir"] == "pixiv":
        pg.setdefault(r["file"].rsplit("_p", 1)[0], []).append(r)
print("\n== pixiv 作品分类 ==")
print("多页素材组 (>=8 页):")
for pid, ws in sorted(pg.items(), key=lambda kv: -len(kv[1])):
    if len(ws) >= 8:
        print("  %s %-40s p%-2d 主尺寸 %dx%d" % (pid, works[pid]["title"][:40], len(ws), ws[0]["w"], ws[0]["h"]))
print("\n单页/少页 (1-7 页):")
for pid, ws in sorted(pg.items()):
    if len(ws) < 8:
        print("  %s %-40s p%-2d %dx%d" % (pid, works[pid]["title"][:40], len(ws), ws[0]["w"], ws[0]["h"]))
