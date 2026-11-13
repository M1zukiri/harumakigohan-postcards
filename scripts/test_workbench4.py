# 2026/10/27 08:35:00 创建 —— 笔刷与压感自检：11 支笔刷预览、模拟数位板压力事件
import sys, os, json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
OUT = r"D:\Harumakigohan\tmp"
errors, res = [], {}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(700)

    res["brush_count"] = pg.eval_on_selector_all(".brush", "els=>els.length")
    res["brush_labels"] = pg.eval_on_selector_all(".brush div", "els=>els.map(e=>e.textContent)")
    res["groups"] = pg.eval_on_selector_all(".brushGroup", "els=>els.map(e=>e.textContent)")

    # 逐个笔刷画一笔，验证无异常
    box = pg.locator("#view").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    for i, key in enumerate(["round", "marker", "pencil", "chalk", "watercolor", "spray",
                             "neon", "glitter", "rainbow", "bubble", "star"]):
        pg.evaluate("(k)=>{S.brush=k;S.size=18;S.alpha=1;S.color='#2f2f43'}", key)
        y = cy - 120 + i * 22
        pg.mouse.move(cx - 100, y)
        pg.mouse.down()
        for k in range(16):
            pg.mouse.move(cx - 100 + k * 12, y + (k % 3) * 4)
        pg.mouse.up()
        pg.wait_for_timeout(60)
    res["strokes_ok"] = pg.evaluate("()=>S.currentStroke===null")
    pg.screenshot(path=os.path.join(OUT, "wb_6_brushes.png"))

    # 模拟数位板：派发 pointerType=pen 且带 pressure 的事件
    pen_ok = pg.evaluate("""()=>{
      const el=document.getElementById('view');
      const r=el.getBoundingClientRect();
      S.brush='round';S.size=26;S.color='#e05555';S.tool='brush';
      const mk=(x,y,pr)=>new PointerEvent('pointerdown',{clientX:x,clientY:y,pressure:pr,
        pointerType:'pen',pointerId:1,bubbles:true,isPrimary:true,buttons:1});
      // 手动走一遍 down/move/up
      const x0=r.left+120,y0=r.top+120;
      el.dispatchEvent(new PointerEvent('pointerdown',{clientX:x0,clientY:y0,pressure:0.1,
        pointerType:'pen',pointerId:7,bubbles:true,isPrimary:true,buttons:1}));
      for(let i=1;i<=20;i++){
        el.dispatchEvent(new PointerEvent('pointermove',{clientX:x0+i*14,clientY:y0,
          pressure:0.1+0.9*(i/20),pointerType:'pen',pointerId:7,bubbles:true,isPrimary:true,buttons:1}));
      }
      el.dispatchEvent(new PointerEvent('pointerup',{clientX:x0+20*14,clientY:y0,pressure:0,
        pointerType:'pen',pointerId:7,bubbles:true,isPrimary:true}));
      return {penMode:!!S.penMode, status:document.getElementById('stPen').textContent,
              strokeDone:S.currentStroke===null};
    }""")
    res["pen_sim"] = pen_ok
    pg.screenshot(path=os.path.join(OUT, "wb_7_pressure.png"))
    b.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
print("errors:", errors)
