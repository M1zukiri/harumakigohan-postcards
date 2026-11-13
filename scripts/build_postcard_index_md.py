# 2026/10/27 00:35:00 创建 —— 由 postcard-index.json 渲染人读索引文档
import os, json, sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
d = json.load(open(os.path.join(M, "postcard-index.json"), encoding="utf-8"))

front = d["front_pool"]
el = d["element_pool"]
songs = d["songs"]
custom = d["custom"]

L = []
A = L.append
A("# 明信片素材索引")
A("")
A("> 生成：2026-10-27　数据源：video/（51 个视频）、image/pixiv（262 张 / 107 作品）、image/custom（55 张）")
A("> 机读版本：`postcard-index.json`（同目录）")
A("")
A("## 一、成品规格与判定规则")
A("")
A("| 项目 | 值 |")
A("|---|---|")
A("| 成品尺寸 | 10×15cm（竖版），300ppi |")
A("| 成品像素 | 1228×1819（比例 0.675） |")
A("| 正面 | 一张完整画面，源图裁成 0.675 竖版后不放大或少放大 |")
A("| 背面 | 曲目元素贴纸，来源为 MV 画面、pixiv 分镜原图、插画局部 |")
A("")
A("像素可用性按“裁到 0.675 竖版后需要的放大倍数”分级：")
A("")
A("| 级别 | 放大倍数 | 实际输出 ppi | 含义 |")
A("|---|---|---|---|")
A("| A | ≤1.00 | ≥300 | 原生足够，最佳 |")
A("| B | 1.00–1.30 | 230–300 | 轻微插值，可接受 |")
A("| C | 1.30–2.00 | 150–230 | 明显放大，仅背面贴纸可用 |")
A("| D | >2.00 | <150 | 不可用于印刷 |")
A("")
A("“保留率”= 裁切后面积 / 原图面积。横图裁竖版会大量丢画面，保留率低于 60% 的需要重新构图。")
A("")

# 概览
A("## 二、素材概览")
A("")
A("| 类别 | 数量 | 说明 |")
A("|---|---|---|")
used_vids = {fp for x in el if x["source"] == "MV 视频" for fp in x["files"]}
A("| 视频 | 51 | %d 条单曲 MV 影音 + %d 条动画／Live／宣传影像 |" % (len(used_vids), 51 - len(used_vids)))
A("| pixiv 作品 | 107（262 张） | 本家原创 88、他人 IP 二创／模写 19 |")
A("| pixiv 分镜组 | 10 组（≥3 页，1920×1080） | MV 与动画的逐页原图，贴纸元素最佳来源 |")
A("| 正面候选 | %d | A 档：无需插值放大即可输出 1228×1819 |" % len(front))
A("| 其他图片 | 55 | 二次分享图、pixiv 转存、社交平台截图 |")
A("")
have = [s for s in songs if s["mv"] or s["pixiv"]]
A("89 首曲目中，本目录**有可视素材的 %d 首**；其余 %d 首仅有音频或无任何本地素材。" % (len(have), len(songs) - len(have)))
A("")

# 曲目索引
A("## 三、曲目素材索引")
A("")
A("“MV 文件”列出已下载到 `video/` 的影音；“pixiv”列出与该曲目直接相关的作品及正面评级。")
A("")
A("| 曲目 | 日期 | MV 影音文件 | pixiv 关联素材 |")
A("|---|---|---|---|")
for s in have:
    mvtxt = []
    for m in s["mv"]:
        if m["files"]:
            mvtxt.append("%s（%s，%d 条）" % (m["title"][:22], m["files"][0]["res"], len(m["files"])))
        else:
            mvtxt.append("%s（未下载）" % m["title"][:22])
    pxtxt = []
    for p in s["pixiv"]:
        pxtxt.append("%s %dp %s [%s]" % (p["title"][:20], p["pages"], p["size"], p["grade"]))
    A("| %s｜%s | %s | %s | %s |" % (
        s["title_ja"], s["title_zh"] or "-", s["release_date"],
        "<br>".join(mvtxt) or "—", "<br>".join(pxtxt) or "—"))
A("")

# 正面候选
A("## 四、正面整图候选（%d 张，均为 A 档）" % len(front))
A("")
A("A 档＝源图裁成 0.675 竖版后不小于 1228×1819，出图无需插值放大。保留率只反映构图损失，供挑图时参考。")
A("")
for label, lo, hi in (("首选：保留率 ≥75%", 0.75, 1.01),
                      ("可用：保留率 60–75%", 0.60, 0.75),
                      ("需重新构图：保留率 40–60%", 0.40, 0.60),
                      ("横图裁竖版，损失大：<40%", 0.0, 0.40)):
    grp = [x for x in front if lo <= x["keep"] < hi]
    grp.sort(key=lambda x: (x["grade"], -x["keep"]))
    if not grp:
        continue
    A("### " + label + "（%d 张）" % len(grp))
    A("")
    A("| 文件 | 作品 | 尺寸 | 等级 | 裁后 | 保留率 | 关联曲目 |")
    A("|---|---|---|---|---|---|---|")
    for x in grp:
        A("| `%s` | %s | %s | %s | %s | %.0f%% | %s |" % (
            x["file"], x["title"], x["size"], x["grade"], x["cut"], x["keep"] * 100,
            x["song_title"][:24]))
    A("")

# 元素来源
A("## 五、背面元素来源")
A("")
A("### 5.1 pixiv 分镜组（逐页 1920×1080 原图）")
A("")
A("MV 的逐页原图，可直接裁出角色、道具、场景作为贴纸，质量高于视频截帧。")
A("")
A("| 作品 | 页数 | 对应曲目／内容 | 文件前缀 |")
A("|---|---|---|---|")
for e in sorted([x for x in el if x["source"] == "pixiv 分镜组"], key=lambda x: -x["count"]):
    A("| %s | %d | %s | `%s_p*` |" % (e["title"], e["count"], (e["song_title"] or "")[:34], e["files"][0].rsplit("_p", 1)[0]))
A("")
A("### 5.2 MV 视频（可截帧）")
A("")
A("| 曲目 | MV 文件 | 分辨率 |")
A("|---|---|---|")
for e in sorted([x for x in el if x["source"] == "MV 视频"], key=lambda x: x["song"]):
    for fp in e["files"]:
        A("| %s | `%s` | %s |" % (e["song_title"][:26], fp, e["size"]))
A("")

# 5.3 未归属单曲的其他影像
dl = json.load(open(os.path.join(M, "_draft_links.json"), encoding="utf-8"))
vfiles, vtitles = dl["video_files"], dl["video_titles"]
rest = [k for k in vfiles if vfiles[k]["file"] not in used_vids]
A("### 5.3 其他影像（动画／Live／宣传，%d 条）" % len(rest))
A("")
A("不对应单一曲目 MV，但含大量可用于背面的演出画面与企划视觉。")
A("")
A("| 文件 | 内容 | 分辨率 | 时长 |")
A("|---|---|---|---|")
for k in sorted(rest):
    d0 = vfiles[k]
    t = vtitles.get(k, {}).get("title", "")
    A("| `%s` | %s | %s | %d:%02d |" % (d0["file"], t[:52], d0["res"],
                                      d0["dur_s"] // 60, d0["dur_s"] % 60))
A("")

# 独立素材
A("## 六、独立素材（不隶属单一曲目）")
A("")
A("含贺图、角色图、企划插画与早期原创插画，可作正面主图或气氛元素。")
A("")
A("| 作品 | 日期 | 尺寸 | 页数 | 等级 | 说明 |")
A("|---|---|---|---|---|---|")
for s in sorted(d["standalone"], key=lambda x: x["date"], reverse=True):
    A("| %s | %s | %s | %d | %s | %s |" % (s["title"], s["date"], s["size"], s["pages"],
                                          s["grade"], s["note"]))
A("")

# 非本家
A("## 七、非本家素材（不建议用于明信片）")
A("")
A("pixiv 早期投稿中的他人 IP 二创、模写与他曲插画：")
A("")
for n in d["non_original"]:
    A("- %s（%s）— %s，`%s`" % (n["title"], n["date"], "／".join(n["tags"]), n["files"][0]))
A("")

# custom
A("## 八、其他图片（image/custom，%d 张）" % len(custom))
A("")
A("完整分类见 `custom-classified.md`。按画面性质：pixiv 重复 14、独立插画 19、MV／动画画面 8、Q 版素材 11、手办照片 1、低清小图 2。")
A("")
A("独立插画中可作明信片正面的（1228×1819 评级 A/B）：")
A("")
A("| 文件 | 尺寸 | 等级 | 内容 | 来源判断 |")
A("|---|---|---|---|---|")
cls = {r["file"]: r for r in json.load(open(os.path.join(M, "custom-classified.json"), encoding="utf-8"))}
for c in sorted(custom, key=lambda x: (x["grade"], -x["keep"])):
    info = cls.get(c["file"], {})
    if info.get("cat") == "illust" and c["grade"] in ("A", "B"):
        A("| `%s` | %s | %s | %s | %s |" % (c["file"], c["size"], c["grade"], c["desc"], c["src"]))
A("")
A("这部分素材多来自小红书／微博／闲鱼二次分享，带平台压缩与水印，正式印刷前需溯源原图。")
A("")

# 缺口
A("## 九、缺口")
A("")
A("1. **早期曲目无本地影像**：2014–2015 年 8 首（`song-001`–`song-008`）只存在于 niconico，本目录无对应视频，做这些曲目只能靠插画或补源。")
A("2. **部分 MV 条目缺影音**：`メルティランドナイトメア（本家演唱）`、`再会`（VOCALOID 版）、`約束`（VOCALOID 版）、`ぽかぽかの星`、`秘密`（VOCALOID 版）、`彗星になれたなら`（VOCALOID 版）、`誕生`（VOCALOID 版）、`フランケンX`、`幻影（本家演唱）`、`ディナーベル（本家演唱）`、`ドッペルゲンガー Character Covers` 共 11 支未下载。")
A("3. **pixiv 缺 2016 年前的部分封面图**：曲绘是否为 pixiv 原图未经逐张核对；`pixiv-works.json` 仅含本账号 107 个作品。")
A("4. **55 张 custom 图来源未确认**：其中 8 张可对应到已归档 pixiv 作品（同名 `illust_*` 文件），其余需按平台水印溯源。")
A("")
A("---")
A("")
A("## 十、下一步")
A("")
A("1. 确认明信片张数与选曲（从第三节有素材的 %d 首中挑）。" % len(have))
A("2. 确认每张正面的主图来源（第四节候选，或另行指定）。")
A("3. 确认背面元素范围（第五节分镜组／MV 截帧／插画抠图）。")
A("4. 制作流程：主图裁切缩放至 1228×1819 → 元素抠图与排版 → 导出 300ppi 印刷文件。")
A("")

open(os.path.join(M, "postcard-index.md"), "w", encoding="utf-8").write("\n".join(L))
print("wrote postcard-index.md lines=", len(L))
