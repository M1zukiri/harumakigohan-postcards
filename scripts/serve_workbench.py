# 2026/10/27 06:40:00 创建 —— 明信片工作台本地服务（静态页 + 贴纸索引 + 任务/导出接口）
import base64
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs

ROOT = r"D:\Harumakigohan"
WB = os.path.join(ROOT, "postcards", "_workbench")
STICKERS = os.path.join(WB, "stickers")
TASKS = os.path.join(WB, "tasks")
OUT = os.path.join(WB, "out")
PALETTES = os.path.join(WB, "palettes.json")
AUTOSAVE = os.path.join(WB, "autosave")
PORT = 54830

for d in (STICKERS, TASKS, OUT, AUTOSAVE):
    os.makedirs(d, exist_ok=True)

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".svg": "image/svg+xml"}


def groups():
    out = []
    root = os.path.join(ROOT, "postcards")
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p) or d.startswith("_"):
            continue
        bg = orient = size = None
        bgd = os.path.join(p, "bg")
        if os.path.isdir(bgd):
            for f in sorted(os.listdir(bgd)):
                if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                try:
                    from PIL import Image
                    with Image.open(os.path.join(bgd, f)) as im:
                        w, h = im.size
                    bg, size = f, [w, h]
                    orient = "landscape" if w > h else "portrait"
                except Exception:
                    pass
                break
        out.append({"name": d, "bg": bg, "orientation": orient, "bg_size": size})
    return out


def palettes():
    if os.path.exists(PALETTES):
        return json.load(open(PALETTES, encoding="utf-8"))
    return {}


def sticker_files():
    out = []
    if not os.path.isdir(STICKERS):
        return out
    for sub in sorted(os.listdir(STICKERS)):
        d = os.path.join(STICKERS, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith((".png", ".webp")):
                continue
            p = os.path.join(d, f)
            out.append({"name": f, "folder": sub,
                        "url": "/stickers/%s/%s" % (sub, f),
                        "bytes": os.path.getsize(p)})
    return out


def tasks():
    out = []
    if not os.path.isdir(TASKS):
        return out
    for f in sorted(os.listdir(TASKS)):
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(open(os.path.join(TASKS, f), encoding="utf-8"))
        except Exception:
            continue
        j["json"] = f
        j["type"] = "mask" if f.startswith("M") else "extract"
        j["done"] = os.path.exists(os.path.join(TASKS, f.replace(".json", ".done")))
        j["skipped"] = os.path.exists(os.path.join(TASKS, f.replace(".json", ".skip")))
        out.append(j)
    return out


def save_data_url(data_url, path):
    m = re.match(r"data:(image/\w+);base64,(.*)", data_url, re.S)
    if not m:
        raise ValueError("bad data url")
    ext = {"image/png": ".png", "image/jpeg": ".jpg"}.get(m.group(1), ".png")
    if not path.lower().endswith(ext):
        path = os.path.splitext(path)[0] + ext
    with open(path, "wb") as f:
        f.write(base64.b64decode(m.group(2)))
    return path


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        if not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        ctype = MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)
        if p in ("/", "/index.html"):
            return self._file(os.path.join(WB, "index.html"))
        if p == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if p == "/api/state":
            return self._send(200, {"root": ROOT, "groups": groups(), "palettes": palettes(),
                                    "canvas": {"w": 1298, "h": 1889, "bleed": 35,
                                               "trim_w": 1228, "trim_h": 1819},
                                    "stickers": sticker_files(), "tasks": tasks()})
        if p == "/api/stickers":
            return self._send(200, {"stickers": sticker_files()})
        if p == "/api/tasks":
            return self._send(200, {"tasks": tasks()})
        if p == "/api/palettes":
            return self._send(200, palettes())
        if p == "/api/autosave":
            q = parse_qs(u.query)
            grp = (q.get("group") or [""])[0]
            fp = os.path.join(AUTOSAVE, re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", grp) + ".json")
            if not grp or not os.path.isfile(fp):
                return self._send(200, {"exists": False})
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                data["exists"] = True
                return self._send(200, data)
            except Exception as e:
                return self._send(200, {"exists": False, "error": str(e)})
        if p.startswith("/stickers/"):
            return self._file(os.path.join(STICKERS, p[len("/stickers/"):].replace("/", os.sep)))
        if p.startswith("/bg/"):
            rest = p[len("/bg/"):].split("/", 1)
            if len(rest) != 2:
                return self._send(404, {"error": "bad bg path"})
            grp, fname = rest
            safe = os.path.normpath(os.path.join(ROOT, "postcards", grp, "bg", fname))
            if not safe.startswith(os.path.join(ROOT, "postcards")):
                return self._send(403, {"error": "forbidden"})
            return self._file(safe)
        if p.startswith("/out/"):
            return self._file(os.path.join(OUT, p[len("/out/"):]))
        if p.startswith("/taskimg/"):
            return self._file(os.path.join(TASKS, p[len("/taskimg/"):]))
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        p = unquote(u.path)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._send(400, {"error": "bad json"})
        if p == "/api/task":
            tid = time.strftime("T%Y%m%d_%H%M%S")
            img = data.pop("image", None)
            data["id"] = tid
            data["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if img:
                path = save_data_url(img, os.path.join(TASKS, tid + ".png"))
                data["image_file"] = os.path.basename(path)
            with open(os.path.join(TASKS, tid + ".json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            return self._send(200, {"ok": True, "id": tid})
        if p == "/api/mask":
            mid = time.strftime("M%Y%m%d_%H%M%S")
            img = data.pop("image", None)
            msk = data.pop("mask", None)
            if not img or not msk:
                return self._send(400, {"error": "image and mask required"})
            data["id"] = mid
            data["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
            ip = save_data_url(img, os.path.join(TASKS, mid + ".png"))
            mp = save_data_url(msk, os.path.join(TASKS, mid + "_mask.png"))
            data["image_file"] = os.path.basename(ip)
            data["mask_file"] = os.path.basename(mp)
            with open(os.path.join(TASKS, mid + ".json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            return self._send(200, {"ok": True, "id": mid})
        if p == "/api/autosave":
            grp = data.get("group") or ""
            if not grp:
                return self._send(400, {"error": "no group"})
            safe = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", grp)
            fp = os.path.join(AUTOSAVE, safe + ".json")
            data["saved"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = fp + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, fp)
            return self._send(200, {"ok": True, "saved": data["saved"],
                                    "bytes": os.path.getsize(fp)})
        if p == "/api/sticker/save":
            folder = (data.get("folder") or "").strip()
            name = (data.get("name") or "").strip()
            img = data.get("image")
            overwrite = bool(data.get("overwrite"))
            if not folder or not name or not img:
                return self._send(400, {"error": "folder, name and image required"})
            safe_folder = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", folder)
            d = os.path.join(STICKERS, safe_folder)
            if not os.path.isdir(d):
                return self._send(404, {"error": "folder not found"})
            stem = os.path.splitext(name)[0]
            safe_stem = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", stem) or "sticker"
            target = os.path.join(d, safe_stem + ".png")
            if overwrite:
                if not os.path.isfile(os.path.join(d, name)):
                    return self._send(404, {"error": "sticker not found"})
                target = os.path.join(d, name)
            elif os.path.exists(target):
                target = os.path.join(d, "%s_%s.png" % (safe_stem, time.strftime("%m%d_%H%M%S")))
            path = save_data_url(img, target)
            return self._send(200, {"ok": True, "folder": safe_folder,
                                    "name": os.path.basename(path),
                                    "url": "/stickers/%s/%s" % (safe_folder, os.path.basename(path)),
                                    "bytes": os.path.getsize(path)})
        if p == "/api/export":
            img = data.get("image")
            group = data.get("group") or "unknown"
            if not img:
                return self._send(400, {"error": "no image"})
            ts = time.strftime("%Y%m%d_%H%M%S")
            side = data.get("side") or "fg"
            safe = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", group)
            base = os.path.join(OUT, "%s_%s_%s.png" % (safe, side, ts))
            path = save_data_url(img, base)
            # 写入 300dpi 元数据
            try:
                from PIL import Image
                im = Image.open(path)
                im.save(path, dpi=(300, 300))
            except Exception as e:
                sys.stderr.write("dpi write failed: %s\n" % e)
            return self._send(200, {"ok": True, "path": path, "url": "/out/" + os.path.basename(path),
                                    "bytes": os.path.getsize(path)})
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("workbench: http://127.0.0.1:%d/" % PORT, flush=True)
    srv.serve_forever()
