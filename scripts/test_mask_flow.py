# 2026-10-27 02:30:00 手工蒙版端到端自检：上传截图、涂保留/去掉、提交、校验文件落盘
import sys, os, json, glob
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
ROOT = r"D:\Harumakigohan"
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
IMG = os.path.join(TASKS, "T20261027_005710.png")
OUT = os.path.join(ROOT, "tmp")
errors, res = [], {}

before = set(glob.glob(os.path.join(TASKS, "M*.json")))

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)

    pg.click('.tabs button[data-tab="mask"]')
    pg.wait_for_timeout(200)
    pg.set_input_files("#maskFile", IMG)
    pg.wait_for_timeout(900)
    res["canvas"] = pg.evaluate("()=>({w:maskCanvas.width,h:maskCanvas.height})")
    res["css"] = pg.evaluate("()=>{const r=maskCanvas.getBoundingClientRect();return {w:Math.round(r.width),h:Math.round(r.height)}}")

    box = pg.locator("#maskCanvas").bounding_box()

    def paint(fx1, fy1, fx2, fy2, hold=False):
        x1 = box["x"] + box["width"] * fx1
        y1 = box["y"] + box["height"] * fy1
        x2 = box["x"] + box["width"] * fx2
        y2 = box["y"] + box["height"] * fy2
        pg.mouse.move(x1, y1)
        pg.mouse.down()
        pg.mouse.move(x2, y2, steps=12)
        pg.mouse.up()

    # 保留：覆盖两个角色所在的矩形区（模拟用户的密集涂抹）
    pg.eval_on_selector("#maskSize", "el=>{el.value=90;el.dispatchEvent(new Event('input'))}")
    for k in range(6):
        fx = 0.385 + k * 0.042
        paint(fx, 0.38, fx, 0.90)
    # 去掉：两人手臂之间的天空
    pg.click('#maskPills .pill[data-m="drop"]')
    pg.eval_on_selector("#maskSize", "el=>{el.value=60;el.dispatchEvent(new Event('input'))}")
    paint(0.585, 0.50, 0.60, 0.60)
    # 撤销一次再画回，验证撤销不报错
    pg.click("#maskUndo")
    pg.click('#maskPills .pill[data-m="keep"]')
    paint(0.585, 0.50, 0.60, 0.60)
    pg.fill("#maskDesc", "自检：保留两个角色与脚下草地，去掉中间天空")
    pg.click("#maskSubmit")
    pg.wait_for_timeout(1600)
    res["status"] = pg.text_content("#stInfo")
    res["rows"] = pg.eval_on_selector_all("#maskList .taskline", "els=>els.length")
    pg.screenshot(path=os.path.join(OUT, "wb_mask_panel.png"))
    b.close()

after = set(glob.glob(os.path.join(TASKS, "M*.json")))
new = sorted(after - before)
res["new_jobs"] = [os.path.basename(x) for x in new]
if new:
    t = json.load(open(new[-1], encoding="utf-8"))
    res["job"] = {k: t.get(k) for k in ("id", "group", "mode", "desc", "image_file", "mask_file")}
    for k in ("image_file", "mask_file"):
        fp = os.path.join(TASKS, t.get(k, ""))
        if os.path.exists(fp):
            from PIL import Image
            import numpy as np
            with Image.open(fp) as im:
                arr = np.array(im.convert("RGBA"))
                info = [im.size, os.path.getsize(fp)]
                if k == "mask_file":
                    nonempty = int((arr[..., 3] > 40).sum())
                    info.append({"painted_px": nonempty})
                res[k] = info
print(json.dumps(res, ensure_ascii=False, indent=1))
print("errors:", errors)
