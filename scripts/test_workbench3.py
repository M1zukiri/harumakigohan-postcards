# 2026/10/27 08:10:00 创建 —— 版式自检：竖/横画布切换、自动按 bg 方向、导出尺寸
import sys, os, json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
OUT = r"D:\Harumakigohan\tmp"
WB_OUT = r"D:\Harumakigohan\postcards\_workbench\out"
errors = []
res = {}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)

    res["groups"] = pg.evaluate("()=>window.__DATA__.groups.map(g=>[g.name,g.orientation,g.bg_size])")
    res["initial"] = pg.evaluate("()=>({layout:S.layout,w:S.canvasW,h:S.canvasH})")

    for grp, expect in (("Futarino2", "landscape"), ("Futarino3", "landscape"),
                        ("G04-G07_コバルトメモリーズ_セブンティーナ", "landscape"),
                        ("G13_第三の心臓", "portrait")):
        pg.select_option("#groupSel", grp)
        pg.wait_for_timeout(250)
        got = pg.evaluate("()=>({layout:S.layout,w:S.canvasW,h:S.canvasH,btn:document.getElementById('layoutBtn').textContent})")
        res[grp] = {"expect": expect, **got, "ok": got["layout"] == expect}

    # 在横版下画一笔并导出
    pg.select_option("#groupSel", "Futarino2")
    pg.wait_for_timeout(250)
    box = pg.locator("#view").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx - 40, cy)
    pg.mouse.down()
    for i in range(8):
        pg.mouse.move(cx - 40 + i * 12, cy + (i % 3) * 10)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.click("#exportBtn")
    pg.wait_for_timeout(1600)
    res["export_status"] = pg.text_content("#stInfo")
    pg.screenshot(path=os.path.join(OUT, "wb_5_landscape.png"))
    b.close()

outs = sorted([f for f in os.listdir(WB_OUT) if f.endswith(".png")])
if outs:
    from PIL import Image
    im = Image.open(os.path.join(WB_OUT, outs[-1]))
    res["export_file"] = outs[-1]
    res["export_size"] = im.size
print(json.dumps(res, ensure_ascii=False, indent=1))
print("errors:", errors)
