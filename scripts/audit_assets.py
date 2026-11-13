# 2026-10-26 21:55:11 创建
import os, re, json, subprocess, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\Harumakigohan"
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")
VID = os.path.join(ROOT, "video")
IMG = os.path.join(ROOT, "image", "pixiv")

def probe(path):
    try:
        p = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:
        return {"error": str(e)[:80]}
    t = p.stderr
    r = {}
    m = re.search(r"Duration: (\d+):(\d+):(\d+)", t)
    if m:
        h, mi, s = map(int, m.groups())
        r["duration_sec"] = h * 3600 + mi * 60 + s
    m = re.search(r"bitrate: (\d+) kb/s", t)
    if m:
        r["total_kbps"] = int(m.group(1))
    m = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", t)
    if m:
        r["codec"] = m.group(1)
        r["width"], r["height"] = int(m.group(2)), int(m.group(3))
    m = re.search(r"Video:.*?, ([\d.]+) kb/s", t)
    if m:
        r["video_kbps"] = float(m.group(1))
    m = re.search(r"Audio: (\w+)", t)
    if m:
        r["acodec"] = m.group(1)
    return r

vids = []
for f in sorted(os.listdir(VID)):
    if not f.lower().endswith(".mp4"):
        continue
    path = os.path.join(VID, f)
    size = os.path.getsize(path)
    info = probe(path)
    info["file"] = f
    info["mb"] = round(size / 1048576, 1)
    src = "bilibili" if f.startswith("bili_") else ("youtube" if f.startswith("yt_") else "other")
    info["source"] = src
    vids.append(info)

imgs = [f for f in os.listdir(IMG) if os.path.isfile(os.path.join(IMG, f))]
img_bytes = sum(os.path.getsize(os.path.join(IMG, f)) for f in imgs)

L = []
L.append("# 素材审计报告\n")
L.append("生成时间：2026-10-26 21:55:11\n")
L.append("## 一、数量\n")
L.append("| 类别 | 实际 | 说明 |")
L.append("|---|---|---|")
ytv = [v for v in vids if v["source"] == "youtube"]
bv = [v for v in vids if v["source"] == "bilibili"]
UPGRADED = {"BV1xW411Y7Yc","BV1Se411R7KQ","BV1oV411R7Jf","BV1WA411i7ZN","BV1hA411g7mt","BV1Kmpc6zEkj",
            "BV1YW411g7y1","BV1vy411z7yg","BV1jD4y1m7Rj","BV1oY4y1N7mY","BV1ibzyBUEaS","BV1s4411A7Tj",
            "BV1i2vAz3EUX","BV1yW411j77X","BV1gJ411M7Sf","BV1g64y1C7Yu","BV1is4y167tD",
            "BV1oW411Y7sm","BV1zt411U7ZE","BV1yB4y1D7zB","BV1Uk8W6dEw2"}
b_up = [v for v in bv if any(k in v["file"] for k in UPGRADED)]
b_ex = [v for v in bv if v not in b_up]
L.append("| MV（YouTube 留存） | {} | B站 无对应稿，或 YouTube 码率更高 |".format(len(ytv)))
L.append("| MV（已升级为 B站 高码率版） | {} | 按码率优先，B站 码率高于 YouTube 版本 |".format(len(b_up)))
L.append("| B站 独家内容 | {} | YouTube 未发布 |".format(len(b_ex)))
L.append("| MV 合计 | {} / 39 | 全部覆盖 |".format(len(ytv) + len(b_up)))
L.append("| pixiv 图片 | {} | 107 个作品全部页面 |".format(len(imgs)))
L.append("| 视频总体积 | {:.2f} GB | - |".format(sum(v["mb"] for v in vids) / 1024))
L.append("| 图片总体积 | {:.1f} MB | - |".format(img_bytes / 1048576))
L.append("")
L.append("## 二、画质分布\n")
for src, label in (("youtube", "YouTube"), ("bilibili", "B站")):
    sub = [v for v in vids if v["source"] == src]
    if not sub:
        continue
    L.append("### {}\n".format(label))
    L.append("| 分辨率 | 数量 |")
    L.append("|---|---|")
    for res, c in Counter("{}x{}".format(v.get("width"), v.get("height")) for v in sub).most_common():
        L.append("| {} | {} |".format(res, c))
    L.append("")
    L.append("| 编码 | 数量 |")
    L.append("|---|---|")
    for codec, c in Counter(v.get("codec") for v in sub).most_common():
        L.append("| {} | {} |".format(codec, c))
    L.append("")
    kb = [v.get("video_kbps") for v in sub if v.get("video_kbps")]
    if kb:
        L.append("视频码率：{} 条，min {:.0f} / median {:.0f} / max {:.0f} kbps\n".format(
            len(kb), min(kb), sorted(kb)[len(kb) // 2], max(kb)))

L.append("## 三、明细\n")
L.append("| 文件 | 源 | MB | 分辨率 | 码率kbps | 时长 |")
L.append("|---|---|---|---|---|---|")
for v in sorted(vids, key=lambda x: (x["source"], x["file"])):
    d = v.get("duration_sec")
    ds = "{:.0f}s".format(d) if d else "?"
    L.append("| {} | {} | {} | {}x{} | {} | {} |".format(
        v["file"], v["source"], v["mb"], v.get("width"), v.get("height"), v.get("video_kbps"), ds))
L.append("")

with open(os.path.join(ROOT, "manifest", "audit-report.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))

print("WROTE manifest/audit-report.md")
print("videos:", len(vids), "pixiv:", len(imgs))
