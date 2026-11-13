# 2026-10-26 21:38:54 创建
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")

root = r"D:\Harumakigohan"

def read_any(p):
    b = open(p, "rb").read()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16")
    return b.decode("utf-8-sig")

# 画质探测结果
qual = {}
for line in read_any(os.path.join(root, "logs", "quality-probe2.txt")).splitlines():
    parts = line.strip().split("|")
    if len(parts) >= 5 and parts[2].isdigit():
        qual[parts[0]] = {"w": int(parts[1]) if parts[1].isdigit() else 0,
                          "h": int(parts[2]), "tbr": parts[3], "fid": parts[4]}

vids = json.load(open(os.path.join(root, "manifest", "youtube-channel.json"), encoding="utf-8"))
cat = json.load(open(os.path.join(root, "manifest", "catalog.json"), encoding="utf-8"))
bili_raw = json.load(open(os.path.join(root, "manifest", "bilibili.json"), encoding="utf-8"))
bili = bili_raw.get("videos", bili_raw) if isinstance(bili_raw, dict) else bili_raw

for v in vids:
    q = qual.get(v["_id"], {})
    v["height"] = q.get("h")
    v["tbr"] = q.get("tbr")

mv_title = {}
for c in cat:
    if c.get("type") == "mv":
        mv_title[str(c.get("id", ""))] = c.get("title_zh") or c.get("title_ja")

order = [("vocaloid", "Vocaloid / 合作 MV"), ("selfcover", "Self Cover（本人演唱）"),
         ("anime", "原创动画《お姉ちゃんごっこ》"), ("live", "Live 版本"),
         ("promo", "宣传物料（SPOT / crossfade / teaser）"), ("other", "其他")]
groups = {k: [] for k, _ in order}
for v in vids:
    groups.setdefault(v["category"], []).append(v)

L = []
L.append("# 素材总览与勾选清单\n")
L.append("生成时间：" + "2026-10-26 21:38:54")
L.append("")
L.append("## 一、平台源能力对比（实测）\n")
L.append("| 平台 | 官方账号 | 可获取内容 | 最高画质 | 限制 |")
L.append("|---|---|---|---|---|")
L.append("| YouTube | HarumakiGohan Official `UCgbTJ0Qb1OpA0GEocaJ7qrw` | 82 条视频（66 长视频 + 15 Shorts + 1 直播） | 1080p/24fps（新作）、720p（老作） | 需代理；无官方 MV 播放列表，需频道全枚举 |")
L.append("| B站 | 春卷饭 `mid 251134371` | 59 条投稿（官方 MV 25 + 动画 2 话 + 预告 + 直播回放 + Blu-ray 衍生） | 登录态 1080P；匿名 480P | 无原生 4K；《无梦之梦》原始版、《宇宙分解》缺档 |")
L.append("| pixiv | `2217467` | 插画 105 / 漫画 2 | 原图（`img-original`） | 必须带 Referer；扩展名需从 ajax 接口取 |")
L.append("| X | `@harumaki_gohan` | 发图（样本约每周 3–4 条） | `?name=orig`（CDN 最大副本） | 非原始上传；/media 需登录 |")
L.append("| niconico | `33802565` | 50 投稿 | 720p | 仅作补充源 |")
L.append("")
L.append("## 二、YouTube 视频清单（含实测画质）\n")
for k, label in order:
    items = groups.get(k, [])
    if not items:
        continue
    L.append("### {}（{} 条）\n".format(label, len(items)))
    L.append("| # | 标题 | 时长 | 屏幕 | 播放量 | 勾选 |")
    L.append("|---|---|---|---|---|---|")
    for i, v in enumerate(items, 1):
        t = (v.get("title") or "").replace("|", "\\|")
        secs = v.get("duration_sec") or 0
        dur = "{}:{:02d}".format(int(secs)//60, int(secs) % 60)
        h = v.get("height")
        res = "{}p".format(h) if h else "?"
        L.append("| {} | {} | {} | {} | {} | ☐ |".format(i, t, dur, res, v.get("view_count")))
    L.append("")

L.append("## 三、B站官方投稿（59 条）\n")
L.append("匿名仅 480P，需登录态才可能 1080P。主要用于：官方独家内容（原创动画、直播回放、Blu-ray 衍生）与中文标题对照。\n")
L.append("| # | 标题 | 时长 | 明确来源 | BV号 | 勾选 |")
L.append("|---|---|---|---|---|---|")
for i, b in enumerate(bili, 1):
    t = (b.get("title") or "").replace("|", "\\|")
    secs_b = b.get("duration") or 0
    dur_b = "{}:{:02d}".format(int(secs_b)//60, int(secs_b) % 60)
    L.append("| {} | {} | {} | {} | {} | ☐ |".format(
        i, t, dur_b, "官方" if b.get("is_official") else "转载", b.get("bvid")))
L.append("")

with open(os.path.join(root, "manifest", "master-checklist.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))

print("WROTE manifest/master-checklist.md")
print("youtube items:", len(vids))
for k, label in order:
    print("{:<30} {}".format(label, len(groups.get(k, []))))
print("bilibili items:", len(bili))
