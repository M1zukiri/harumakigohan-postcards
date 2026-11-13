# 2026-10-26 23:18:17 创建
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
rows = json.load(open(os.path.join(ROOT, "manifest", "image-custom-index.json"), encoding="utf-8"))
L = ["# 其他图片素材索引\n",
     "共 {} 个文件。来源未经逐条确认（混有 pixiv 命名、时间戳命名、QQ 与 MD5 命名），按文件名与内容判断为作品相关分享图与截图。\n".format(len(rows)),
     "| # | 文件 | 分辨率 | 格式 | KB |",
     "|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    L.append("| {} | {} | {}x{} | {} | {} |".format(i, r["file"], r["w"], r["h"], r["fmt"], r["kb"]))
with open(os.path.join(ROOT, "manifest", "image-custom-index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("WROTE manifest/image-custom-index.md", len(rows))
