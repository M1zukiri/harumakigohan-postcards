# 2026/10/27 07:20:00 创建 —— 工作台功能自检 v2：贴纸加载/拖拽、任务提交、导出尺寸与 dpi
import sys, os, json, base64
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
ROOT = r"D:\Harumakigohan"
OUT = os.path.join(ROOT, "tmp")
TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
WB_OUT = os.path.join(ROOT, "postcards", "_workbench", "out")

errors = []
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)

    # 1. 贴纸库
    pg.click('.tabs button[data-tab="sticker"]')
    pg.wait_for_timeout(300)
    res["sticker_count"] = pg.eval_on_selector_all("#stickerGrid .item", "els=>els.length")
    res["sticker_names"] = pg.eval_on_selector_all("#stickerGrid .item div", "els=>els.slice(0,4).map(e=>e.textContent)")

    # 2. 加入画布
    pg.click("#stickerGrid .item")
    pg.wait_for_timeout(500)
    res["on_canvas"] = pg.evaluate("()=>S.stickersOnCanvas.length")
    res["selected_tool"] = pg.evaluate("()=>S.tool")

    # 3. 拖动贴纸
    box = pg.locator("#view").bounding_box()
    pos0 = pg.evaluate("()=>({x:S.stickersOnCanvas[0].x,y:S.stickersOnCanvas[0].y})")
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    pg.mouse.move(cx + 80, cy + 60, steps=5)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pos1 = pg.evaluate("()=>({x:S.stickersOnCanvas[0].x,y:S.stickersOnCanvas[0].y})")
    res["drag_delta"] = {"x": round(pos1["x"] - pos0["x"], 1), "y": round(pos1["y"] - pos0["y"], 1)}
    pg.screenshot(path=os.path.join(OUT, "wb_4_sticker.png"))

    # 4. 导出
    pg.click("#exportBtn")
    pg.wait_for_timeout(1500)
    res["export_status"] = pg.text_content("#stInfo")

    # 5. 任务提交（用一张现有插画当截图）
    img_path = os.path.join(ROOT, "image", "pixiv", "89929372_p0.png")
    data_url = "data:image/png;base64," + base64.b64encode(open(img_path, "rb").read()).decode()
    pg.click('.tabs button[data-tab="task"]')
    pg.evaluate("""(d)=>{const im=document.getElementById('taskImg');im.src=d;}""", data_url)
    pg.wait_for_timeout(900)
    pg.fill("#taskDesc", "测试：抠出角色，白边 4px")
    pg.click("#submitTask")
    pg.wait_for_timeout(900)
    res["task_status"] = pg.text_content("#stInfo")
    b.close()

# 校验导出文件
outs = sorted([f for f in os.listdir(WB_OUT) if f.endswith(".png")])
if outs:
    from PIL import Image
    im = Image.open(os.path.join(WB_OUT, outs[-1]))
    res["export_file"] = outs[-1]
    res["export_size"] = im.size
    res["export_dpi"] = im.info.get("dpi")
tasks = sorted([f for f in os.listdir(TASKS) if f.endswith(".json")])
res["task_files"] = tasks[-2:]
if tasks:
    t = json.load(open(os.path.join(TASKS, tasks[-1]), encoding="utf-8"))
    res["task_sample"] = {k: t.get(k) for k in ("id", "group", "mode", "desc", "rect", "image_file")}

print(json.dumps(res, ensure_ascii=False, indent=1))
print("errors:", errors)
