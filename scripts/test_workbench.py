# 2026/10/27 07:05:00 创建 —— 明信片工作台的可交互性自检（截图 + 控制台错误 + 基本操作）
import sys, os, json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
OUT = r"D:\Harumakigohan\tmp"
os.makedirs(OUT, exist_ok=True)

errors, msgs = [], []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("console", lambda m: (errors if m.type == "error" else msgs).append(m.text))
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.screenshot(path=os.path.join(OUT, "wb_1_initial.png"))

    info = {}
    info["title"] = pg.title()
    info["groups"] = pg.eval_on_selector_all("#groupSel option", "els=>els.map(e=>e.value)")
    info["canvas"] = pg.evaluate("({w:view.width,h:view.height})")
    info["zoom"] = pg.text_content("#zoomLabel")
    info["swatches"] = pg.eval_on_selector_all("#swatches .sw",
                                               "els=>els.map(e=>getComputedStyle(e).backgroundColor)")
    info["brushes"] = pg.eval_on_selector_all(".brush", "els=>els.map(e=>e.textContent)")

    if info["groups"]:
        pg.select_option("#groupSel", info["groups"][2])
        pg.wait_for_timeout(200)
        info["swatches_after"] = pg.eval_on_selector_all(
            "#swatches .sw", "els=>els.map(e=>getComputedStyle(e).backgroundColor)")

    box = pg.locator("#view").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx - 60, cy - 40)
    pg.mouse.down()
    for i in range(12):
        pg.mouse.move(cx - 60 + i * 10, cy - 40 + (i % 4) * 8)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    info["stroke_drawn"] = pg.evaluate(
        "()=>{const d=base.getContext('2d').getImageData(0,0,base.width,base.height).data;"
        "for(let i=3;i<d.length;i+=4)if(d[i]>0)return true;return false}")

    for t in ("sticker", "task", "layer", "brush"):
        pg.click(f'.tabs button[data-tab="{t}"]')
        pg.wait_for_timeout(120)
    pg.screenshot(path=os.path.join(OUT, "wb_2_drawn.png"))

    pg.mouse.move(cx, cy)
    pg.mouse.wheel(0, -300)
    pg.wait_for_timeout(200)
    info["zoom_after_wheel"] = pg.text_content("#zoomLabel")
    pg.screenshot(path=os.path.join(OUT, "wb_3_zoom.png"))

    pg.click("#exportBtn")
    pg.wait_for_timeout(1500)
    info["status_after_export"] = pg.text_content("#stInfo")
    b.close()

print(json.dumps(info, ensure_ascii=False, indent=1))
print("errors:", errors)
print("msgs:", msgs[:5])
