# 2026-10-27 01:55:00 用 isnet-anime ONNX 模型给截图区域生成 alpha 掩膜（CPU 推理）
import os

import numpy as np
import cv2
import onnxruntime as ort
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "bin", "isnet-anime.onnx")
SIZE = 1024
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)

_session = None


def session():
    global _session
    if _session is None:
        so = ort.SessionOptions()
        so.log_severity_level = 3
        _session = ort.InferenceSession(MODEL, sess_options=so, providers=["CPUExecutionProvider"])
    return _session


def predict_alpha(rgb, size=SIZE):
    """rgb: HxWx3 uint8 -> HxW float32 in [0,1]."""
    h, w = rgb.shape[:2]
    im = Image.fromarray(rgb).resize((size, size), Image.LANCZOS)
    arr = np.array(im, np.float32) / 255.0
    arr = (arr - MEAN) / STD
    x = arr.transpose(2, 0, 1)[None]
    s = session()
    out = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    out = (out - out.min()) / max(out.max() - out.min(), 1e-6)
    alpha = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(alpha, 0.0, 1.0)


def mask_from_alpha(alpha, thr=0.5, keep_biggest=True, min_area=300):
    m = alpha > thr
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    if keep_biggest:
        from scipy import ndimage
        lab, n = ndimage.label(m)
        if n:
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            keep = [i + 1 for i in range(n) if sizes[i] >= min_area]
            m = np.isin(lab, keep)
    return m


if __name__ == "__main__":
    import sys

    src = sys.argv[1]
    bgr = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_COLOR)
    rgb = bgr[:, :, ::-1]
    a = predict_alpha(rgb)
    print("alpha range", float(a.min()), float(a.max()), "mean", float(a.mean()))
    out = os.path.splitext(src)[0] + "_alpha.png"
    Image.fromarray((a * 255).astype(np.uint8)).save(out)
    print("saved", out)
