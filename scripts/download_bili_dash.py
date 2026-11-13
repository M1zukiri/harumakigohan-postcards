# 2026-10-26 23:13:41 创建
import requests, os, sys, subprocess, time, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
VID = os.path.join(ROOT, "video")
TMP = os.path.join(ROOT, "tmp", "dash")
os.makedirs(TMP, exist_ok=True)
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
cf = os.path.join(os.path.expanduser("~"), ".bilidown", "cookies.txt")

s = requests.Session()
s.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
for line in open(cf, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    p = line.split("\t")
    if len(p) >= 7:
        s.cookies.set(p[5], p[6], domain=p[0], path=p[2])

TARGETS = ["BV1oW411Y7sm", "BV1zt411U7ZE", "BV1yB4y1D7zB", "BV1Uk8W6dEw2"]

def get_streams(bv):
    v = s.get("https://api.bilibili.com/x/web-interface/view", params={"bvid": bv}, timeout=20).json()
    cid = v["data"]["cid"]
    r = s.get("https://api.bilibili.com/x/player/playurl",
              params={"bvid": bv, "cid": cid, "qn": 127, "fnval": 4048, "fourk": 1}, timeout=30).json()
    dash = (r.get("data") or {}).get("dash") or {}
    vs = dash.get("video") or []
    au = dash.get("audio") or []
    if not vs:
        return None
    bv_ = max(vs, key=lambda x: x.get("bandwidth", 0))
    ba = max(au, key=lambda x: x.get("bandwidth", 0)) if au else None
    return bv_, ba

def dl(url, path):
    for attempt in range(3):
        try:
            r = s.get(url, headers={"Referer": "https://www.bilibili.com/"}, stream=True, timeout=120)
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
            if total and done < total * 0.9:
                raise RuntimeError("incomplete %d/%d" % (done, total))
            return done
        except Exception as e:
            print("   retry %d: %s" % (attempt + 1, str(e)[:60]), flush=True)
            time.sleep(3)
    return 0

ok = 0
for idx, bv in enumerate(TARGETS, 1):
    print("[%d/%d] %s" % (idx, len(TARGETS), bv), flush=True)
    st = get_streams(bv)
    if not st:
        print("  no streams", flush=True)
        continue
    vstream, astream = st
    vk = round(vstream["bandwidth"] / 1000)
    vtmp = os.path.join(TMP, bv + ".video.m4s")
    atmp = os.path.join(TMP, bv + ".audio.m4s")
    url = vstream.get("baseUrl") or (vstream.get("backupUrl") or [None])[0]
    n1 = dl(url, vtmp)
    print("  video %dk -> %.0f MB" % (vk, n1 / 1048576), flush=True)
    n2 = 0
    if astream:
        aurl = astream.get("baseUrl") or (astream.get("backupUrl") or [None])[0]
        n2 = dl(aurl, atmp)
        print("  audio -> %.1f MB" % (n2 / 1048576), flush=True)
    out = os.path.join(VID, "bili_%s.mp4" % bv)
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-y", "-i", vtmp]
    if astream:
        cmd += ["-i", atmp]
    cmd += ["-c", "copy", out]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode == 0 and os.path.exists(out):
        ok += 1
        print("  MERGED -> %s %.1f MB" % (out, os.path.getsize(out) / 1048576), flush=True)
        for t in (vtmp, atmp):
            if os.path.exists(t):
                os.remove(t)
    else:
        print("  MERGE FAIL:", (p.stderr or "")[:200], flush=True)

print("DONE ok=%d/%d" % (ok, len(TARGETS)), flush=True)

