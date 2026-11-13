# 2026/10/27 00:35:15 创建 —— 生成共享贴纸（邮票窗／气泡）
import datetime, json, math, os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"D:\Harumakigohan"
WB = os.path.join(ROOT, "postcards", "_workbench")
PALETTES = os.path.join(WB, "palettes.json")
OUTDIR = os.path.join(WB, "stickers", "shared")
PREVIEW = os.path.join(ROOT, "tmp", "shared_stickers_preview.jpg")
INDEX = os.path.join(OUTDIR, "index.json")

S = 2                       # 超采样倍数：2 倍绘制后缩小，获得抗锯齿
STAMP_W, STAMP_H = 708, 944
BUBBLE_W, BUBBLE_H = 900, 620

STAMP_R = 14                # 齿孔半径
STAMP_GAP = 56              # 齿孔间距
STAMP_STROKE = 8            # 主色边宽
STAMP_RULE = 3              # 白色内线宽
RULE_OUTSIDE = True         # 主色边贴轮廓外沿（False 则改为白边在外、彩线在内）
BUBBLE_R = 80               # 对话气泡圆角半径
BUBBLE_STROKE = 10          # 气泡描边宽度


def offset(mask, px, grow):
    """按半径 px 膨胀（grow=True）或腐蚀掩膜。

    高斯模糊后的阶跃边缘在原始边界处恒为 0.5，与 σ 无关；把阈值取到 ±1σ
    对应的高斯累积值即得到约 σ 的偏移量，比 MinFilter/MaxFilter 快得多，
    且拐角自然圆滑。"""
    r = px * S
    if r <= 0:
        return mask
    blurred = mask.filter(ImageFilter.GaussianBlur(r))
    cut = 255 * (0.1587 if grow else 0.8413)
    return blurred.point(lambda v: 255 if v >= cut else 0)


def stamp_silhouette(w, h):
    """竖版矩形 + 四边向外凸出的半圆齿孔，返回轮廓掩膜与几何参数。"""
    r = STAMP_R
    margin = r + 4
    x0, y0, x1, y1 = margin, margin, w - margin, h - margin
    pts = [(x0, y0)]
    counts = []

    def bumps(a, b, nrm):
        ax, ay = a
        bx, by = b
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        n = max(1, round(length / STAMP_GAP))
        step = length / n
        counts.append((n, round(step, 2)))
        for i in range(n):
            cx = ax + ux * step * (i + 0.5)
            cy = ay + uy * step * (i + 0.5)
            for k in range(13):                      # 每齿 12 段折线近似半圆
                t = math.pi * (1 - k / 12)           # π → 0，中点为凸出最远处
                pts.append((cx + ux * r * math.cos(t) + nrm[0] * r * math.sin(t),
                            cy + uy * r * math.cos(t) + nrm[1] * r * math.sin(t)))

    bumps((x0, y0), (x1, y0), (0, -1))               # 上
    bumps((x1, y0), (x1, y1), (1, 0))                # 右
    bumps((x1, y1), (x0, y1), (0, 1))                # 下
    bumps((x0, y1), (x0, y0), (-1, 0))               # 左

    mask = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(mask).polygon([(x * S, y * S) for x, y in pts], fill=255)
    geom = {"base_rect": [x0, y0, x1, y1], "bumps": dict(zip(("top", "right", "bottom", "left"),
                                                            counts))}
    return mask, geom


def make_stamp(primary):
    """轮廓最外 8px 主色边 + 其内 3px 白色内线，再往里全部透明。

    白色描边在白卡面上不可见，故边框主体用主色，白色只作内侧分离线；
    齿孔凸出 14px，8px 主色边不会磨平齿形。RULE_OUTSIDE=False 则改为
    白边在外、彩线在里（浅底上几乎不可见）。
    """
    w, h = STAMP_W, STAMP_H
    sil, geom = stamp_silhouette(w, h)
    a1 = offset(sil, STAMP_STROKE, False)                      # 轮廓内缩 8px
    a2 = offset(sil, STAMP_STROKE + STAMP_RULE, False)         # 轮廓内缩 11px
    if RULE_OUTSIDE:
        rule = ImageChops.subtract(sil, a1)                    # 0~8px  主色边
        band = ImageChops.subtract(a1, a2)                     # 8~11px 白色内线
    else:
        band = ImageChops.subtract(sil, offset(sil, STAMP_STROKE, False))   # 0~8px
        rule = ImageChops.subtract(offset(sil, STAMP_STROKE, False), a2)    # 8~11px

    img = Image.new("RGBA", sil.size, (255, 255, 255, 255))
    img.putalpha(ImageChops.lighter(band, rule))      # 边框之外保持透明
    img.paste((255, 255, 255, 255), mask=band)
    img.paste(primary + (255,), mask=rule)
    return img.resize((w, h), Image.LANCZOS), geom


def bubble_image(sil, inner, color, w, h):
    """轮廓填主色，inner 区域填白，缩小即得主色描边 + 白色内芯。"""
    rgb = Image.new("RGBA", sil.size, color + (255,))
    rgb.paste((255, 255, 255, 255), mask=inner)
    img = rgb.copy()
    img.putalpha(sil)
    return img.resize((w, h), Image.LANCZOS)


def make_speech(primary):
    w, h = BUBBLE_W, BUBBLE_H
    sil = Image.new("L", (w * S, h * S), 0)
    d = ImageDraw.Draw(sil)
    d.rounded_rectangle([12 * S, 12 * S, 880 * S, 478 * S], radius=BUBBLE_R * S, fill=255)
    d.polygon([(200 * S, 415 * S), (350 * S, 478 * S), (92 * S, 590 * S)], fill=255)
    return bubble_image(sil, offset(sil, BUBBLE_STROKE, False), primary, w, h), {}


CLOUD = [   # (cx, cy, rx, ry)：中部大椭圆兜底 + 9 个边缘团块
    (300, 250, 220, 160),
    (110, 300, 100, 88),
    (150, 190, 95, 82),
    (270, 130, 105, 88),
    (400, 140, 100, 85),
    (510, 220, 100, 85),
    (560, 330, 95, 82),
    (450, 390, 105, 85),
    (300, 400, 110, 82),
    (190, 380, 95, 78),
]
DOTS = [(735, 480, 32), (800, 545, 22), (848, 596, 13)]


def make_thought(primary):
    w, h = BUBBLE_W, BUBBLE_H
    sil = Image.new("L", (w * S, h * S), 0)
    clouds = Image.new("L", (w * S, h * S), 0)
    dc = ImageDraw.Draw(clouds)
    for cx, cy, rx, ry in CLOUD:
        dc.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=255)
    d = ImageDraw.Draw(sil)
    sil.paste(clouds)
    for cx, cy, r in DOTS:                       # 圆点为实心主色，不参与白色内芯
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=255)
    return bubble_image(sil, offset(clouds, BUBBLE_STROKE, False), primary, w, h), {}


def slug_of(group):
    """组名 → 安全短码：取首个下划线前的编号段（如 G13_第三の心臓 → G13）。"""
    head = group.split("_")[0]
    keep = "".join(c if (c.isalnum() or c in "-") else "_" for c in head)
    while "__" in keep:
        keep = keep.replace("__", "_")
    return keep.strip("_")


def main():
    with open(PALETTES, encoding="utf-8") as f:
        palettes = json.load(f)
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)

    builders = (("stamp", make_stamp, STAMP_W, STAMP_H),
                ("speech", make_speech, BUBBLE_W, BUBBLE_H),
                ("thought", make_thought, BUBBLE_W, BUBBLE_H))

    items, groups, built = [], {}, []
    for group, meta in palettes.items():
        slug = slug_of(group)
        colors = meta.get("colors") or []
        primary = tuple(colors[0]["rgb"]) if colors else (40, 40, 40)
        primary_hex = colors[0]["hex"].upper() if colors else "#282828"
        secondary_hex = colors[1]["hex"].upper() if len(colors) > 1 else None
        entry = {"group": group, "slug": slug, "primary_hex": primary_hex,
                 "secondary_hex": secondary_hex, "files": {}}
        for kind, build, w, h in builders:
            name = "%s_%s.png" % (kind, slug)
            path = os.path.join(OUTDIR, name)
            img, info = build(primary)
            img.save(path)
            size = os.path.getsize(path)
            items.append({"file": name, "type": kind, "group": group, "slug": slug,
                          "primary_hex": primary_hex, "secondary_hex": secondary_hex,
                          "width": img.width, "height": img.height, "bytes": size,
                          "geometry": info})
            entry["files"][kind] = name
            built.append((kind, img, group, slug, name, size))
            print("%-22s %4d×%-4d %7.1f KB  %s" % (name, img.width, img.height,
                                                   size / 1024, primary_hex))
        groups[group] = entry

    index = {
        "generated_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "source": os.path.relpath(PALETTES, ROOT).replace("\\", "/"),
        "supersample": S,
        "types": {
            "stamp": {"width": STAMP_W, "height": STAMP_H,
                      "spec": "竖版矩形窗，内部完全透明；轮廓最外 %dpx 主色边 + 其内 %dpx 白色内线；"
                              "四边半圆齿孔 r=%d px、间距 %d px 向外凸出"
                              % (STAMP_STROKE, STAMP_RULE, STAMP_R, STAMP_GAP)},
            "speech": {"width": BUBBLE_W, "height": BUBBLE_H,
                       "spec": "圆角矩形 r=%d + 左下角尾巴，白底主色描边 %dpx"
                               % (BUBBLE_R, BUBBLE_STROKE)},
            "thought": {"width": BUBBLE_W, "height": BUBBLE_H,
                        "spec": "%d 个椭圆叠成云朵轮廓 + 右下 3 个实心圆点，白底主色描边 %dpx"
                                % (len(CLOUD), BUBBLE_STROKE)},
        },
        "files": items,
        "groups": groups,
    }
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

    make_preview(built, list(palettes.keys()))
    print("index: %s (%d 条)" % (INDEX, len(items)))
    print("preview: %s" % PREVIEW)


def make_preview(built, group_order):
    """每行一类形状、每列一组配色的拼图，深色底便于看清白色描边。"""
    order = ["stamp", "speech", "thought"]
    cell_w, cell_h, pad = 300, 360, 12
    head, foot = 64, 34
    sheet_w = cell_w * len(group_order)
    sheet_h = head + cell_h * len(order) + foot
    sheet = Image.new("RGB", (sheet_w, sheet_h), (26, 26, 32))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
    small = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
    alias = {g: slug_of(g) for g in group_order}

    for ci, group in enumerate(group_order):
        x = ci * cell_w
        draw.line([(x, 0), (x, sheet_h)], fill=(48, 48, 56))
        draw.text((x + 10, 22), alias[group], fill=(240, 240, 245), font=font)

    for ri, kind in enumerate(order):
        y = head + ri * cell_h
        draw.line([(0, y), (sheet_w, y)], fill=(60, 60, 70))
        draw.text((10, y + 8), kind, fill=(150, 200, 235), font=small)
        for ci, group in enumerate(group_order):
            _, img, _, slug, _, _ = next(b for b in built if b[0] == kind and b[2] == group)
            k = min((cell_w - 2 * pad) / img.width, (cell_h - 2 * pad - 18) / img.height)
            thumb = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))),
                               Image.LANCZOS)
            px = ci * cell_w + (cell_w - thumb.width) // 2
            py = y + (cell_h - thumb.height) // 2
            sheet.paste(thumb, (px, py), thumb)
            draw.text((ci * cell_w + 10, y + cell_h - 24), "%s  %d×%d" % (slug, img.width, img.height),
                      fill=(120, 120, 135), font=small)

    sheet.save(PREVIEW, quality=92)
    print("preview %d×%d" % sheet.size)


if __name__ == "__main__":
    main()
