# 2026-10-27 02:20:00 读取工作台提交的手工蒙版任务，生成线稿贴纸
import os
import sys
import json
import glob

import numpy as np
import cv2
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

TASKS = os.path.join(ROOT, "postcards", "_workbench", "tasks")
OUT = os.path.join(ROOT, "postcards", "_workbench", "out", "stickers")

import make_line_stickers as M


def load_mask(path, shape):
    """解码涂抹图：绿=保留，红=去掉，其余=未指定。"""
    a = np.array(Image.open(path).convert("RGBA"))
    if a.shape[:2] != shape:
        a = np.array(Image.fromarray(a).resize((shape[1], shape[0]), Image.NEAREST))
    R = a[..., 0].astype(np.int16)
    G = a[..., 1].astype(np.int16)
    B = a[..., 2].astype(np.int16)
    A = a[..., 3]
    painted = A > 40
    keep = painted & (G > 130) & (R < 130) & (B < 130)
    drop = painted & (R > 130) & (G < 130) & (B < 130)
    return keep, drop


def refine_with_seeds(bgr, base, keep, drop):
    """以模型结果为主体，红色笔迹直接挖掉；再用 GrabCut 把边界修一遍。"""
    h, w = base.shape
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    gc[base] = cv2.GC_PR_FGD
    gc[drop] = cv2.GC_BGD
    bgm = np.zeros((1, 65), np.float64)
    fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc, None, bgm, fgm, 4, cv2.GC_INIT_WITH_MASK)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m[drop] = False
    # 只保留与模型主体相连的部分，防止 GrabCut 乱扩张
    lab, n = ndimage.label(m)
    if n:
        seed_lab = np.bincount(lab[base].ravel(), minlength=n + 1)
        m = np.isin(lab, [i for i in range(1, n + 1) if seed_lab[i] > 0])
    return m


def subject_in_region(bgr, region):
    """在涂抹划定的范围内找主体：优先 isnet-anime，失败时退回颜色分割。"""
    rgb = bgr[:, :, ::-1]
    try:
        from ai_cutout import predict_alpha
        a = predict_alpha(rgb)
        cand = (a > 0.5) & region
        if cand.sum() > max(400, int(region.sum() * 0.01)):
            return cand, "ai"
    except Exception as e:
        sys.stderr.write("ai cutout skipped: %s\n" % e)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    S = hsv[..., 1].astype(np.int16)
    V = hsv[..., 2].astype(np.int16)
    R, G, B = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    dark = (V < 175) & (S > 90) & (B >= G)
    cand = dark & region
    if cand.sum() < 400:
        return region.copy(), "region"
    return cand, "color"


def build(job, detail=0.0, line_w=3):
    j = json.load(open(job, encoding="utf-8"))
    img_path = os.path.join(TASKS, j["image_file"])
    mask_path = os.path.join(TASKS, j["mask_file"])
    bgr = M.imread(img_path)
    h, w = bgr.shape[:2]

    keep, drop = load_mask(mask_path, (h, w))
    if not keep.any() and not drop.any():
        raise RuntimeError("蒙版是空的")

    # 涂抹只用来划定范围；范围内的主体交给模型判断，涂宽了也不会把背景带进来
    if keep.any():
        region = cv2.dilate(keep.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
        region &= ~drop
        base, how = subject_in_region(bgr, region)
    else:
        base = np.zeros((h, w), bool)
        how = "drop-only"

    mask = refine_with_seeds(bgr, base, keep, drop)
    mask = M.solidify(mask, 3, 200, 600)

    line = M.compose_lines(mask, bgr, width=line_w, detail=detail)
    out_rgb, out_a = M.make_lines_rgba(bgr, line, mask, 1)

    name = "mask_%s_线稿.png" % j["id"]
    path = os.path.join(OUT, name)
    M.save_rgba(path, out_rgb, out_a)
    return path, j, how


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = sorted(glob.glob(os.path.join(TASKS, "M*.json")))
    if len(sys.argv) > 1:
        jobs = [p for p in jobs if sys.argv[1] in os.path.basename(p)]
    if not jobs:
        print("没有蒙版任务")
        sys.exit(0)
    for job in jobs:
        try:
            path, j, how = build(job)
            print("ok", os.path.basename(path), "mode=" + how, j.get("group"), str(j.get("desc", ""))[:30])
        except Exception as e:
            print("fail", os.path.basename(job), e)
