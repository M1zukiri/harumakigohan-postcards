# 2026-10-26 21:44:39 创建
import requests, json, os, time, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\Harumakigohan"
OUT = os.path.join(ROOT, "image", "pixiv")
LOGJ = os.path.join(ROOT, "manifest", "pixiv-download.jsonl")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

s = requests.Session()
s.headers.update({"User-Agent": UA, "Referer": "https://www.pixiv.net/", "Accept-Language": "zh-CN,zh;q=0.9"})
s.proxies = PX

prof = s.get("https://www.pixiv.net/ajax/user/2217467/profile/all?lang=zh", timeout=30).json()
b = prof.get("body") or {}
ids = list((b.get("illusts") or {}).keys())
manga = list((b.get("manga") or {}).keys())
allids = [(i, "illust") for i in ids] + [(i, "manga") for i in manga]
print("WORKS", len(allids), flush=True)

rec_f = open(LOGJ, "w", encoding="utf-8")
files = 0
bytes_total = 0
fails = []
for n, (pid, kind) in enumerate(allids, 1):
    try:
        time.sleep(0.7)
        pg = s.get("https://www.pixiv.net/ajax/illust/%s/pages?lang=zh" % pid, timeout=30).json()
        if pg.get("error"):
            fails.append((pid, "pages:" + str(pg.get("message"))))
            print("[%d/%d] %s FAIL %s" % (n, len(allids), pid, pg.get("message")), flush=True)
            continue
        page_urls = [p["urls"]["original"] for p in pg["body"]]
        for pi, url in enumerate(page_urls):
            ext = os.path.splitext(url.split("?")[0])[1] or ".png"
            name = "%s_p%d%s" % (pid, pi, ext)
            path = os.path.join(OUT, name)
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                files += 1
                continue
            time.sleep(0.4)
            r = s.get(url, headers={"Referer": "https://www.pixiv.net/"}, timeout=90)
            if r.status_code == 200 and len(r.content) > 1024:
                with open(path, "wb") as f:
                    f.write(r.content)
                files += 1
                bytes_total += len(r.content)
                rec_f.write(json.dumps({"id": pid, "kind": kind, "page": pi, "file": name,
                                        "bytes": len(r.content), "url": url}, ensure_ascii=False) + "\n")
                rec_f.flush()
            else:
                fails.append((pid, "http:%s" % r.status_code))
                print("[%d/%d] %s p%d http %s" % (n, len(allids), pid, pi, r.status_code), flush=True)
        if n % 10 == 0:
            print("[%d/%d] files=%d MB=%.1f" % (n, len(allids), files, bytes_total / 1048576), flush=True)
    except Exception as e:
        fails.append((pid, "exc:" + str(e)[:60]))
        print("[%d/%d] %s EXC %s" % (n, len(allids), pid, str(e)[:60]), flush=True)

rec_f.close()
print("DONE files=%d MB=%.1f fails=%d" % (files, bytes_total / 1048576, len(fails)), flush=True)
for p, r in fails[:20]:
    print("FAIL", p, r, flush=True)
