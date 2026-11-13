# 2026/10/27 08:50:00 创建 —— 压感渲染验证：对不同 pressure 值检查笔迹宽度是否递增
import sys, os, json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:54830/"
OUT = r"D:\Harumakigohan\tmp"
errors = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)

    # 压力递增的笔迹，检查不同 x 处的笔画高度
    widths = pg.evaluate("""()=>{
      const cv=document.createElement('canvas');cv.width=700;cv.height=200;
      const c=cv.getContext('2d');c.fillStyle='#fff';c.fillRect(0,0,700,200);
      const pts=[];
      for(let i=0;i<40;i++)pts.push({x:30+i*15,y:100,p:i/39,sp:5});
      brushStroke(c,pts,'round','#1b3f5f',44,1);
      const out=[];
      for(const x of [40,180,340,500,620]){
        let n=0;const d=c.getImageData(x,0,1,200).data;
        for(let i=0;i<200;i++)if(d[i*4]<240||d[i*4+1]<240||d[i*4+2]<240)n++;
        out.push({x,height:n});
      }
      return out;
    }""")

    # 鼠标（无压感）速度调制：sp 大则细
    speed = pg.evaluate("""()=>{
      const mk=(sp)=>{const cv=document.createElement('canvas');cv.width=300;cv.height=120;
        const c=cv.getContext('2d');c.fillStyle='#fff';c.fillRect(0,0,300,120);
        const pts=[];for(let i=0;i<20;i++)pts.push({x:20+i*12,y:60,p:-1,sp:sp});
        brushStroke(c,pts,'round','#1b3f5f',30,1);
        let n=0;const d=c.getImageData(150,0,1,120).data;
        for(let i=0;i<120;i++)if(d[i*4]<240||d[i*4+1]<240||d[i*4+2]<240)n++;
        return n;};
      return {slow:mk(2),fast:mk(40)};
    }""")

    # 11 种笔刷渲染，横向排列放大查看
    pg.evaluate("""()=>{
      const cv=document.createElement('canvas');cv.width=1200;cv.height=760;
      const c=cv.getContext('2d');c.fillStyle='#ffffff';c.fillRect(0,0,1200,760);
      const kinds=['round','marker','pencil','chalk','watercolor','spray',
                   'neon','glitter','rainbow','bubble','star'];
      const labels=['round','marker','pencil','chalk','water','spray','neon','glitter','rainbow','bubble','star'];
      c.font='16px sans-serif';
      kinds.forEach((k,i)=>{
        const y=60+i*64;
        c.fillStyle='#888';c.fillText(labels[i],20,y+8);
        const pts=[];
        for(let j=0;j<34;j++){
          const t=j/33;
          pts.push({x:150+t*960,y:y+Math.sin(t*9)*14,p:0.15+0.85*Math.abs(Math.sin(t*3.4)),sp:5});
        }
        brushStroke(c,pts,k,'#1b3f5f',16,1);
      });
      window.__SHEET__=cv;
    }""")
    pg.evaluate("""()=>{
      const src=window.__SHEET__;
      const img=document.createElement('img');
      document.body.appendChild(img);
      img.id='sheetimg';img.src=src.toDataURL('image/png');
      img.style.cssText='position:fixed;left:0;top:0;z-index:9999;width:1200px';
    }""")
    pg.wait_for_timeout(500)
    pg.locator("#sheetimg").screenshot(path=os.path.join(OUT, "wb_8_brushsheet.png"))
    b.close()

print("pressure widths:", json.dumps(widths, ensure_ascii=False))
print("speed widths:", json.dumps(speed, ensure_ascii=False))
print("errors:", errors)
