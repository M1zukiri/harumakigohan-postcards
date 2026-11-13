# 2026/10/27 02:55:00 创建 —— 缺插画曲目抽 3 帧取画面信息量最大者（避开标题卡/纯色帧）
import os, json, sys, subprocess, glob
from PIL import Image, ImageStat

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
M = os.path.join(ROOT, "manifest")
OUT = os.path.join(ROOT, "tmp", "mvshots")
TMP = os.path.join(ROOT, "tmp", "mvshots_tmp")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")

rows = json.load(open(os.path.join(M, "postcard-song-groups.json"), encoding="utf-8"))
for r in rows:
    if r["status"] != "need-illust":
        continue
    f = r["mv"][0]
    src = os.path.join(ROOT, "video", f["file"])
    dst = os.path.join(OUT, r["song_id"] + ".jpg")
    best, best_score = None, -1.0
    for idx, frac in enumerate((0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90)):
        cand = os.path.join(TMP, "%s_%d.jpg" % (r["song_id"], idx))
        ss = max(4, int(f["dur_s"] * frac))
        try:
            subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(ss), "-i", src,
                            "-frames:v", "1", "-q:v", "2", "-vf", "scale=1920:-2", cand],
                           check=True, timeout=120)
            with Image.open(cand) as im:
                g = im.convert("L").resize((320, 180))
                stat = ImageStat.Stat(g)
                # 信息量：标准差高且非纯白/纯黑
                score = stat.stddev[0] * (1.0 - abs(stat.mean[0] - 128) / 400)
            if score > best_score:
                best_score, best = score, cand
        except Exception as e:
            print("  frame fail", r["song_id"], idx, str(e)[:60])
    if best:
        os.replace(best, dst)
        print("pick", r["song_id"], r["title"], "frame", best, "std=%.1f" % best_score)
for p in glob.glob(os.path.join(TMP, "*.jpg")):
    try:
        os.remove(p)
    except OSError:
        pass
