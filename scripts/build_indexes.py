# 2026-10-26 22:57:45 创建
import os, re, json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\Harumakigohan"
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")
VID = os.path.join(ROOT, "video")

def probe(path):
    try:
        p = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception:
        return {}
    t = p.stderr
    r = {}
    m = re.search(r"Duration: (\d+):(\d+):(\d+)", t)
    if m:
        h, mi, s = map(int, m.groups())
        r["dur"] = h * 3600 + mi * 60 + s
    m = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", t)
    if m:
        r["codec"], r["w"], r["h"] = m.group(1), int(m.group(2)), int(m.group(3))
    m = re.search(r"Video:.*?, ([\d.]+) kb/s", t)
    if m:
        r["vk"] = float(m.group(1))
    return r

yt = json.load(open(os.path.join(ROOT, "manifest", "youtube-channel.json"), encoding="utf-8"))
ytmap = {v["_id"]: v for v in yt}

br = json.load(open(os.path.join(ROOT, "manifest", "bilibili.json"), encoding="utf-8"))
bmap = {v["bvid"]: v for v in br.get("videos", [])}

rows = []
for f in sorted(os.listdir(VID)):
    if not f.lower().endswith(".mp4"):
        continue
    path = os.path.join(VID, f)
    info = probe(path)
    mb = round(os.path.getsize(path) / 1048576, 1)
    m = re.match(r"(yt|bili)_([A-Za-z0-9_-]+)", f)
    src, key = (m.group(1), m.group(2)) if m else ("?", "")
    if src == "yt":
        meta = ytmap.get(key, {})
        title = meta.get("title", "")
        url = "https://www.youtube.com/watch?v=" + key
        platform = "YouTube"
    elif src == "bili":
        meta = bmap.get(key, {})
        title = meta.get("title", "")
        url = "https://www.bilibili.com/video/" + key
        platform = "B站"
    else:
        title, url, platform = "", "", "?"
    d = info.get("dur")
    dur = "{}:{:02d}".format(d // 60, d % 60) if d else "?"
    rows.append({"file": f, "platform": platform, "title": title, "url": url, "mb": mb,
                 "res": "{}x{}".format(info.get("w"), info.get("h")), "vk": info.get("vk"), "dur": dur})

L = ["# 视频素材索引\n", "共 {} 个文件。\n".format(len(rows))]
L.append("| 文件 | 平台 | 标题 | 分辨率 | 码率kbps | 时长 | MB |")
L.append("|---|---|---|---|---|---|---|")
for r in rows:
    t = (r["title"] or "").replace("|", "\\|")[:60]
    L.append("| {} | {} | {} | {} | {} | {} | {} |".format(
        r["file"], r["platform"], t, r["res"], r["vk"], r["dur"], r["mb"]))
L.append("")
L.append("原始链接：\n")
for r in rows:
    L.append("- `{}` → {}".format(r["file"], r["url"]))

with open(os.path.join(ROOT, "manifest", "video-index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))

px = sorted(os.listdir(os.path.join(ROOT, "image", "pixiv")))
L2 = ["# pixiv 图片索引\n", "共 {} 张原图，来自 107 个作品（user 2217467）。\n".format(len(px))]
L2.append("文件命名规则：`<作品ID>_p<页码>.<扩展名>`，原图来自 `i.pximg.net/img-original/`。\n")
L2.append("| # | 文件 | MB |")
L2.append("|---|---|---|")
for i, f in enumerate(px, 1):
    p = os.path.join(ROOT, "image", "pixiv", f)
    L2.append("| {} | {} | {:.2f} |".format(i, f, os.path.getsize(p) / 1048576))
with open(os.path.join(ROOT, "manifest", "pixiv-index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L2))

print("WROTE video-index.md (%d), pixiv-index.md (%d)" % (len(rows), len(px)))
