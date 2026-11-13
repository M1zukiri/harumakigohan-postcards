# 2026/10/27 04:05:00 创建 —— custom 55 张分类：pixiv 重复 / MV 截图 / Q 版素材 / 独立插画 / 照片 / 低清小图
import os, json, sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
notes = json.load(open(os.path.join(M, "postcard-custom-notes.json"), encoding="utf-8"))
dup = {x["file"]: x for x in json.load(open(os.path.join(M, "custom-vs-pixiv.json"), encoding="utf-8"))}
dims = {r["file"]: r for r in json.load(open(os.path.join(M, "image-dimensions.json"), encoding="utf-8"))
        if r["dir"] == "custom"}
works = {w["id"]: w for w in json.load(open(os.path.join(M, "pixiv-works.json"), encoding="utf-8"))}

# 人工判定：MV/动画截图、Q 版素材、独立插画、照片、低清小图
CATEGORY = {
    "1652012609990.png": "mv-frame",
    "1691843333567.png": "mv-frame",
    "86b225efa5508e583fe3097160615182.png": "mv-frame",
    "Image_612857970168221.jpg": "mv-frame",
    "c3fba590d4097556511c32fdc508f570.png": "mv-frame",
    "eee862b0aa490437d29276717973bd81.png": "mv-frame",
    "mobileqq_card_pic_1726857803301.jpg": "mv-frame",
    "ふたりの-はるまきごはん (春卷饭).jpg": "mv-frame",
    "1722489114039.gif": "chibi",
    "1770445107946.png": "chibi",
    "1732636745328.jpg": "chibi",
    "1732636747355.jpg": "chibi",
    "Image_1715413097613.jpg": "chibi",
    "Image_1722341306200.jpg": "chibi",
    "Image_1726850778865.jpg": "chibi",
    "Image_1792728542439_34.jpg": "chibi",
    "SAVE_20240826_115908.jpg": "chibi",
    "idlefish-msg-1696777497752.png.jpg": "chibi",
    "idlefish-msg-1696901727319.png.jpg": "chibi",
    "17124637292529e04bd5ede8362a0dbe68a5d98fe79b413d72948.jpg": "lowres",
    "Image_1763915591789.jpg": "lowres",
    "Image_216482776251364.jpg": "photo",
    "74DF59B72D8DCF32E60F213D9FFF0CD8.jpg": "illust",
    "1773817313557.jpeg": "illust",
    "1773817318922.jpeg": "illust",
    "89e6d57dd914885d6981bc7b52e63def.png": "illust",
    "Camera_1040g3k0323b0u526g2405nmuv6a08egnp118o18.jpg": "illust",
    "Camera_XHS_1789298464901.jpg": "illust",
    "Camera_XHS_1791200596583notes_pre_post_1040g3k8325sd9ao34e705nhru9bg8723o4g0o5o.jpg": "illust",
    "Camera_XHS_1791536272657notes_pre_post_1040g3k0325t679rk58dg5oj08cck1rhelhhr9eg.jpg": "illust",
    "Camera_XHS_1791779100203notes_pre_post_1040g3k8325ujlnlel8005oj08cck1rhe2k455lg.jpg": "illust",
    "Camera_XHS_17930058776191040g008326pfcamcl06g5nmuv6a08egn1h450kg.jpg": "illust",
    "Image_1728923511205.png": "illust",
    "Image_1791523279763_299.jpg": "illust",
    "Image_1791523359969_766.jpg": "illust",
    "Image_1792260824060_814.png": "illust",
    "Image_384755546154393.jpg": "illust",
    "Image_78780890460387.jpg": "illust",
    "b4bb576b3953b34bb694173f079dd67d.jpg": "illust",
    "illust_108214536_20231009_112905.jpg": "illust",
    "illust_96210863_20231010_114443.jpg": "illust",
}
LABEL = {"dup": "pixiv 重复", "mv-frame": "MV／动画画面", "chibi": "Q 版素材",
         "illust": "独立插画", "photo": "手办照片", "lowres": "低清小图"}

TW, TH = 1228, 1819


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


rows = []
for f, d0 in sorted(dims.items()):
    dd = dup.get(f, {})
    if dd.get("dup"):
        cat = "dup"
    else:
        cat = CATEGORY.get(f, "unclassified")
    n = notes.get(f, {})
    cw, ch, scale, keep, grade = fit(d0["w"], d0["h"])
    match = dd.get("pixiv_match")
    mtitle = ""
    if match:
        pid = match.rsplit("_p", 1)[0]
        mtitle = works.get(pid, {}).get("title", "") or pid
    rows.append({"file": f, "cat": cat, "label": LABEL.get(cat, "未分类"),
                 "w": d0["w"], "h": d0["h"], "g": grade, "scale": scale, "keep": keep,
                 "cut": "%dx%d" % (cw, ch), "desc": n.get("desc", ""), "src": n.get("src", ""),
                 "dup_of": match if cat == "dup" else None, "dup_title": mtitle,
                 "dist": dd.get("dist")})

from collections import Counter
print(Counter(r["cat"] for r in rows))
print("\n== 独立插画中可作正面的（A 档）==")
for r in rows:
    if r["cat"] == "illust" and r["g"] == "A":
        print("  %-52s %5dx%-5d %s scale=%.2f keep=%.0f%% | %s" % (
            r["file"][:52], r["w"], r["h"], r["g"], r["scale"], r["keep"] * 100, r["desc"][:30]))

json.dump(rows, open(os.path.join(M, "custom-classified.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# 人读报告
L = []
A = L.append
A("# image/custom 分类结果（55 张）")
A("")
A("生成：2026-10-27　方法：感知哈希与 pixiv 262 张原图逐张比对，再按画面内容人工分类。")
A("")
cnt = Counter(r["cat"] for r in rows)
A("| 类别 | 数量 | 说明 |")
A("|---|---|---|")
A("| pixiv 重复 | %d | 与已归档 pixiv 原图同图，仅作备份，不参与选材 |" % cnt["dup"])
A("| MV／动画截图 | %d | 从 MV 或动画截下的画面，可作背面元素，不作插画 |" % cnt["mv-frame"])
A("| Q 版素材 | %d | 头像、表情、四格，多为二次创作或衍生图 |" % cnt["chibi"])
A("| 独立插画 | %d | 不在 pixiv 归档中的插画作品 |" % cnt["illust"])
A("| 手办照片 | %d | 实体周边实拍 |" % cnt["photo"])
A("| 低清小图 | %d | 尺寸不足以印刷 |" % cnt["lowres"])
A("")
A("## 一、pixiv 重复（%d 张）" % cnt["dup"])
A("")
A("| 文件 | 对应 pixiv 作品 | 哈希距离 |")
A("|---|---|---|")
for r in rows:
    if r["cat"] == "dup":
        A("| `%s` | %s `%s` | %d |" % (r["file"], r["dup_title"], r["dup_of"], r["dist"]))
A("")
A("## 二、独立插画（%d 张）" % cnt["illust"])
A("")
A("| 文件 | 尺寸 | 正面评级 | 裁后 | 内容 | 来源 |")
A("|---|---|---|---|---|---|")
for r in rows:
    if r["cat"] == "illust":
        A("| `%s` | %dx%d | %s | %s | %s | %s |" % (
            r["file"], r["w"], r["h"], r["g"], r["cut"], r["desc"], r["src"]))
A("")
A("## 三、MV／动画截图（%d 张）" % cnt["mv-frame"])
A("")
A("| 文件 | 尺寸 | 内容 |")
A("|---|---|---|")
for r in rows:
    if r["cat"] == "mv-frame":
        A("| `%s` | %dx%d | %s |" % (r["file"], r["w"], r["h"], r["desc"]))
A("")
A("## 四、Q 版素材与低清小图（%d 张）" % (cnt["chibi"] + cnt["lowres"] + cnt["photo"]))
A("")
A("| 文件 | 类别 | 尺寸 | 内容 |")
A("|---|---|---|---|")
for r in rows:
    if r["cat"] in ("chibi", "lowres", "photo"):
        A("| `%s` | %s | %dx%d | %s |" % (r["file"], r["label"], r["w"], r["h"], r["desc"]))
A("")
A("## 结论")
A("")
A("- custom 并非全部是插画：%d 张是 pixiv 原图的副本，%d 张是 MV／动画截图，%d 张是 Q 版衍生或低清图。" %
  (cnt["dup"], cnt["mv-frame"], cnt["chibi"] + cnt["lowres"] + cnt["photo"]))
A("- 真正可作明信片正面的独立插画有 %d 张（A 档：无需插值放大），其余分辨率或构图不足。" %
  sum(1 for r in rows if r["cat"] == "illust" and r["g"] == "A"))
A("- 这 %d 张里没有能对应到缺 A 档插画曲目的整图；画面内容以角色特写、双人图、季节插画为主，不属单曲曲绘。" %
  sum(1 for r in rows if r["cat"] == "illust"))
open(os.path.join(M, "custom-classified.md"), "w", encoding="utf-8").write("\n".join(L))
print("\n-> custom-classified.md / .json")
