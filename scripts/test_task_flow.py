# 2026/10/27 09:05:00 创建 —— 提取任务端到端自检：上传截图、框选、提交，校验坐标与文件落盘
import sys, os, json, glob
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
ROOT = r"D:\Harumakigohan"
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
IMG = os.path.join(ROOT, "image", "pixiv", "89929372_p0.png")   # 1280x1920
OUT = os.path.join(ROOT, "tmp")
errors, res = [], {}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)

    pg.click('.tabs button[data-tab="task"]')
    pg.set_input_files("#taskFile", IMG)
    pg.wait_for_timeout(900)
    res["natural"] = pg.evaluate("()=>({w:taskImg.naturalWidth,h:taskImg.naturalHeight})")
    res["display"] = pg.evaluate("()=>{const r=taskImg.getBoundingClientRect();return {w:r.width,h:r.height}}")

    # 在图片上框选一块（显示坐标 30%,20% 到 70%,55%）
    box = pg.locator("#taskCanvasWrap").bounding_box()
    x1 = box["x"] + box["width"] * 0.30
    y1 = box["y"] + box["height"] * 0.20
    x2 = box["x"] + box["width"] * 0.70
    y2 = box["y"] + box["height"] * 0.55
    pg.mouse.move(x1, y1)
    pg.mouse.down()
    pg.mouse.move(x2, y2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.fill("#taskDesc", "测试任务：抠出角色上半身，白边 5px，去掉背景文字")
    pg.click("#submitTask")
    pg.wait_for_timeout(1200)
    res["status"] = pg.text_content("#stInfo")
    res["task_rows"] = pg.eval_on_selector_all("#taskList .taskline", "els=>els.length")
    pg.screenshot(path=os.path.join(OUT, "wb_9_task.png"))
    b.close()

files = sorted(glob.glob(os.path.join(TASKS, "*.json")))
if files:
    t = json.load(open(files[-1], encoding="utf-8"))
    res["latest_task"] = {k: t.get(k) for k in ("id", "group", "mode", "desc", "rect", "image_file")}
    img_path = os.path.join(TASKS, t.get("image_file", ""))
    if os.path.exists(img_path):
        from PIL import Image
        with Image.open(img_path) as im:
            res["saved_image"] = [im.size, os.path.getsize(img_path)]
print(json.dumps(res, ensure_ascii=False, indent=1))
print("errors:", errors)
