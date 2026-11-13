# 2026/10/26 23:32:00 创建 —— 抓取 107 个 pixiv 作品的元数据（标题/标签/日期/页数）
import os, json, sys, time
import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\Harumakigohan"
DIMS = os.path.join(ROOT, "manifest", "image-dimensions.json")
OUT = os.path.join(ROOT, "manifest", "pixiv-works.json")
LOG = os.path.join(ROOT, "logs", "pixiv-meta.log")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

rows = json.load(open(DIMS, encoding="utf-8"))
ids = sorted({r["file"].rsplit("_p", 1)[0] for r in rows if r["dir"] == "pixiv"})
print("works", len(ids), flush=True)

s = requests.Session()
s.headers.update({"User-Agent": UA, "Referer": "https://www.pixiv.net/",
                  "Accept-Language": "zh-CN,zh;q=0.9"})
s.proxies = PX

works = {}
if os.path.exists(OUT):
    works = {w["id"]: w for w in json.load(open(OUT, encoding="utf-8"))}

fails = []
with open(LOG, "a", encoding="utf-8") as log:
    for n, pid in enumerate(ids, 1):
        if pid in works:
            continue
        for attempt in range(3):
            try:
                time.sleep(0.6)
                r = s.get("https://www.pixiv.net/ajax/illust/%s?lang=zh" % pid, timeout=30)
                j = r.json()
                if j.get("error"):
                    raise RuntimeError(j.get("message"))
                b = j["body"]
                works[pid] = {
                    "id": pid,
                    "title": b.get("title"),
                    "description": (b.get("description") or "")[:400],
                    "createDate": b.get("createDate"),
                    "uploadDate": b.get("uploadDate"),
                    "pageCount": b.get("pageCount"),
                    "illustType": b.get("illustType"),
                    "width": b.get("width"),
                    "height": b.get("height"),
                    "tags": [t.get("tag") for t in (b.get("tags") or {}).get("tags", [])],
                    "userName": b.get("userName"),
                    "url": "https://www.pixiv.net/artworks/%s" % pid,
                }
                print("[%d/%d] %s %s" % (n, len(ids), pid, works[pid]["title"]), flush=True)
                log.write("%s OK\n" % pid)
                break
            except Exception as e:
                if attempt == 2:
                    fails.append((pid, str(e)[:80]))
                    print("[%d/%d] %s FAIL %s" % (n, len(ids), pid, str(e)[:80]), flush=True)
                    log.write("%s FAIL %s\n" % (pid, str(e)[:120]))
                else:
                    time.sleep(3)
        if n % 20 == 0:
            json.dump(list(works.values()), open(OUT, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)

json.dump(list(works.values()), open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("DONE works=%d fails=%d -> %s" % (len(works), len(fails), OUT), flush=True)
for f in fails[:20]:
    print("FAIL", f, flush=True)
