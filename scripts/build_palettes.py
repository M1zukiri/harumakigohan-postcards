# 2026/10/27 06:20:00 创建 —— 为 8 个明信片组从各自 MV 提取 3 个主题色
import os, json, subprocess, sys, glob
import numpy as np
import cv2

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
WB = os.path.join(ROOT, "postcards", "_workbench")
TMP = os.path.join(ROOT, "tmp", "palette_frames")
os.makedirs(TMP, exist_ok=True)
os.makedirs(WB, exist_ok=True)
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")

GROUPS = {
    "G04-G07_コバルトメモリーズ_セブンティーナ": "bili_BV1xW411Y7Yc.mp4",
    "G05_メルティランドナイトメア": "bili_BV1yW411j77X.mp4",
    "G13_第三の心臓": "bili_BV1hA411g7mt.mp4",
    "G16_幻影": "yt_V3Q9xT7C1pI.mp4",
    "G21_ゼロトーキング": "bili_BV1Se411R7KQ.mp4",
    "Futarino1": "bili_BV1jL98YXEhs.mp4",
    "Futarino2": "bili_BV1oV411R7Jf.mp4",
    "Futarino3": "bili_BV1gJ411M7Sf.mp4",
}

# 时长（秒），来自 audit-report
DUR = {
    "bili_BV1xW411Y7Yc.mp4": 269, "bili_BV1yW411j77X.mp4": 268, "bili_BV1hA411g7mt.mp4": 209,
    "yt_V3Q9xT7C1pI.mp4": 218, "bili_BV1Se411R7KQ.mp4": 226, "bili_BV1jL98YXEhs.mp4": 3645,
    "bili_BV1oV411R7Jf.mp4": 286, "bili_BV1gJ411M7Sf.mp4": 251,
}


def sample_colors(frames, k=6):
    pix = []
    for f in frames:
        raw = np.fromfile(f, dtype=np.uint8)
        im = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if im is None:
            continue
        im = cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA)
        pix.append(im.reshape(-1, 3))
    if not pix:
        return []
    data = np.concatenate(pix).astype(np.float32)
    rng = np.random.default_rng(42)
    idx = rng.choice(len(data), size=min(60000, len(data)), replace=False)
    data = data[idx]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 6, cv2.KMEANS_PP_CENTERS)
    labels = labels.flatten()
    total = len(labels)
    out = []
    for i, c in enumerate(centers):
        b, g, r = [int(v) for v in c]
        ratio = (labels == i).sum() / total
        # 过滤近黑/近白，避免主题色全变成黑白
        mx, mn = max(b, g, r), min(b, g, r)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        if lum > 0.94 or lum < 0.06:
            continue
        out.append({"hex": "#%02X%02X%02X" % (r, g, b), "rgb": [r, g, b],
                    "ratio": round(float(ratio), 3), "sat": int(mx - mn)})
    out.sort(key=lambda x: -x["ratio"])
    return out[:3]


result = {}
for gi, (g, mv) in enumerate(GROUPS.items()):
    src = os.path.join(ROOT, "video", mv)
    dur = DUR.get(mv, 200)
    frames = []
    for i, frac in enumerate((0.15, 0.35, 0.55, 0.75, 0.9)):
        out = os.path.join(TMP, "g%d_%d.jpg" % (gi, i))
        ss = max(3, int(dur * frac))
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(ss), "-i", src,
                        "-frames:v", "1", "-q:v", "3", "-vf", "scale=640:-2", out],
                       check=False, timeout=120)
        if os.path.exists(out) and os.path.getsize(out) > 5000:
            frames.append(out)
    colors = sample_colors(frames)
    result[g] = {"mv": mv, "colors": colors}
    print(g, "->", ", ".join("%s(%.0f%%)" % (c["hex"], c["ratio"] * 100) for c in colors))

json.dump(result, open(os.path.join(WB, "palettes.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for f in glob.glob(os.path.join(TMP, "*.jpg")):
    os.remove(f)
print("\n->", os.path.join(WB, "palettes.json"))
