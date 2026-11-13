# 2026/10/28 03:15:00 MangaLineExtraction（Deep Extraction of Manga Structural Lines）本地推理封装
# 模型结构来自 https://github.com/ljsabc/MangaLineExtraction_PyTorch ，权重 erika.pth（SIGGRAPH 2017）
import os

import numpy as np
import cv2
import torch
import torch.nn as nn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHT = os.path.join(ROOT, "scripts", "weights", "erika.pth")


class _bn_relu_conv(nn.Module):
    def __init__(self, in_filters, nb_filters, fw, fh, subsample=1):
        super().__init__()
        self.model = nn.Sequential(
            nn.BatchNorm2d(in_filters, eps=1e-3),
            nn.LeakyReLU(0.2),
            nn.Conv2d(in_filters, nb_filters, (fw, fh), stride=subsample, padding=(fw // 2, fh // 2),
                      padding_mode='zeros'))

    def forward(self, x):
        return self.model(x)


class _u_bn_relu_conv(nn.Module):
    def __init__(self, in_filters, nb_filters, fw, fh, subsample=1):
        super().__init__()
        self.model = nn.Sequential(
            nn.BatchNorm2d(in_filters, eps=1e-3),
            nn.LeakyReLU(0.2),
            nn.Conv2d(in_filters, nb_filters, (fw, fh), stride=subsample, padding=(fw // 2, fh // 2)),
            nn.Upsample(scale_factor=2, mode='nearest'))

    def forward(self, x):
        return self.model(x)


class _shortcut(nn.Module):
    def __init__(self, in_filters, nb_filters, subsample=1):
        super().__init__()
        self.process = False
        self.model = None
        if in_filters != nb_filters or subsample != 1:
            self.process = True
            self.model = nn.Sequential(nn.Conv2d(in_filters, nb_filters, (1, 1), stride=subsample))

    def forward(self, x, y):
        if self.process:
            return self.model(x) + y
        return x + y


class _u_shortcut(nn.Module):
    def __init__(self, in_filters, nb_filters, subsample):
        super().__init__()
        self.process = False
        self.model = None
        if in_filters != nb_filters:
            self.process = True
            self.model = nn.Sequential(
                nn.Conv2d(in_filters, nb_filters, (1, 1), stride=subsample, padding_mode='zeros'),
                nn.Upsample(scale_factor=2, mode='nearest'))

    def forward(self, x, y):
        if self.process:
            return self.model(x) + y
        return x + y


class basic_block(nn.Module):
    def __init__(self, in_filters, nb_filters, init_subsample=1):
        super().__init__()
        self.conv1 = _bn_relu_conv(in_filters, nb_filters, 3, 3, subsample=init_subsample)
        self.residual = _bn_relu_conv(nb_filters, nb_filters, 3, 3)
        self.shortcut = _shortcut(in_filters, nb_filters, subsample=init_subsample)

    def forward(self, x):
        return self.shortcut(x, self.residual(self.conv1(x)))


class _u_basic_block(nn.Module):
    def __init__(self, in_filters, nb_filters, init_subsample=1):
        super().__init__()
        self.conv1 = _u_bn_relu_conv(in_filters, nb_filters, 3, 3, subsample=init_subsample)
        self.residual = _bn_relu_conv(nb_filters, nb_filters, 3, 3)
        self.shortcut = _u_shortcut(in_filters, nb_filters, subsample=init_subsample)

    def forward(self, x):
        return self.shortcut(x, self.residual(self.conv1(x)))


class _residual_block(nn.Module):
    def __init__(self, in_filters, nb_filters, repetitions, is_first_layer=False):
        super().__init__()
        layers = []
        for i in range(repetitions):
            init_subsample = 1
            if i == repetitions - 1 and not is_first_layer:
                init_subsample = 2
            l = basic_block(in_filters if i == 0 else nb_filters, nb_filters, init_subsample)
            layers.append(l)
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


class _upsampling_residual_block(nn.Module):
    def __init__(self, in_filters, nb_filters, repetitions):
        super().__init__()
        layers = []
        for i in range(repetitions):
            if i == 0:
                l = _u_basic_block(in_filters, nb_filters)
            else:
                l = basic_block(nb_filters, nb_filters)
            layers.append(l)
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


class res_skip(nn.Module):
    def __init__(self):
        super().__init__()
        self.block0 = _residual_block(1, 24, 2, is_first_layer=True)
        self.block1 = _residual_block(24, 48, 3)
        self.block2 = _residual_block(48, 96, 5)
        self.block3 = _residual_block(96, 192, 7)
        self.block4 = _residual_block(192, 384, 12)
        self.block5 = _upsampling_residual_block(384, 192, 7)
        self.res1 = _shortcut(192, 192)
        self.block6 = _upsampling_residual_block(192, 96, 5)
        self.res2 = _shortcut(96, 96)
        self.block7 = _upsampling_residual_block(96, 48, 3)
        self.res3 = _shortcut(48, 48)
        self.block8 = _upsampling_residual_block(48, 24, 2)
        self.res4 = _shortcut(24, 24)
        self.block9 = _residual_block(24, 16, 2, is_first_layer=True)
        self.conv15 = _bn_relu_conv(16, 1, 1, 1)

    def forward(self, x):
        x0 = self.block0(x)
        x1 = self.block1(x0)
        x2 = self.block2(x1)
        x3 = self.block3(x2)
        x4 = self.block4(x3)
        res1 = self.res1(x3, self.block5(x4))
        res2 = self.res2(x2, self.block6(res1))
        res3 = self.res3(x1, self.block7(res2))
        res4 = self.res4(x0, self.block8(res3))
        return self.conv15(self.block9(res4))


_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        m = res_skip()
        sd = torch.load(WEIGHT, map_location="cpu")
        if isinstance(sd, dict) and "state_dict" in sd:
            sd = sd["state_dict"]
        m.load_state_dict(sd)
        m.eval()
        if torch.cuda.is_available():
            m = m.cuda()
        _MODEL = m
    return _MODEL


@torch.no_grad()
def manga_lines(gray, max_side=1400):
    """输入 uint8 灰度图，返回 0-255 线稿强度（float32）。"""
    m = get_model()
    h0, w0 = gray.shape[:2]
    k = min(1.0, max_side / max(h0, w0))
    if k < 1.0:
        gray = cv2.resize(gray, (max(1, int(w0 * k)), max(1, int(h0 * k))), interpolation=cv2.INTER_AREA)
    h, w = gray.shape[:2]
    rows = int(np.ceil(h / 16)) * 16
    cols = int(np.ceil(w / 16)) * 16
    patch = np.zeros((1, 1, rows, cols), np.float32)
    patch[0, 0, :h, :w] = gray.astype(np.float32)
    t = torch.from_numpy(patch)
    if torch.cuda.is_available():
        t = t.cuda()
    y = m(t).cpu().numpy()[0, 0]
    out = np.clip(y[:h, :w], 0, 255)
    if (h, w) != (h0, w0):
        out = cv2.resize(out, (w0, h0), interpolation=cv2.INTER_LINEAR)
    return out.astype(np.float32)
