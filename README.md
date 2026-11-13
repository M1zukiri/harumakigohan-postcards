# はるまきごはん 明信片工作台与设计稿

10×15 cm 竖版明信片（300 ppi，成品 1228×1819 px）的正面插画、背面线稿，以及绘制明信片用的本地工作台。

## 目录结构

```
postcards/
  <组>/
    bg/               正面插画
    fg/               背面成品（工作台导出）
    ss/ screenshots/  绘制过程截图
    <作品ID>_p<N>.*   同组备用插画
    SOURCES.md        本组素材来源与版权
  _workbench/         明信片工作台
    index.html        界面
    palettes.json     各组配色
    stickers/         线稿贴纸库
    tasks/            提交给工作台的截图与蒙版
    autosave/         画布状态
    SOURCES.md        工作台素材来源
scripts/
  serve_workbench.py  工作台本地服务
requirements.txt
```

## 设计进度

| 组 | 曲目 | 正面 | 背面 | 贴纸 |
| --- | --- | --- | --- | --- |
| `Futarino1` | ふたりの专辑（夜蓝） | ✓ | ✓ | 5 |
| `Futarino2` | ふたりの专辑（暖调） | ✓ | ✓ | 10 |
| `Futarino3` | ふたりの专辑（晴空） | ✓ | ✓ | 11 |
| `G04-G07_コバルトメモリーズ_セブンティーナ` | コバルトメモリーズ／セブンティーナ | ✓ | ✓ | 19 |
| `G05_メルティランドナイトメア` | メルティランドナイトメア | ✓ | — | — |
| `G13_第三の心臓` | 第三の心臓 | ✓ | ✓ | 14 |
| `G16_幻影` | 幻影 | ✓ | — | — |
| `G21_ゼロトーキング` | ゼロトーキング | ✓ | ✓ | 22 |

## 工作台

依赖 Python 3.9+ 与 Pillow：

```powershell
pip install -r requirements.txt
python scripts/serve_workbench.py
```

浏览器打开 <http://127.0.0.1:54830/>。画布 1298×1889，成品 1228×1819 加 35 px 出血。

`scripts/serve_workbench.py` 里的 `ROOT` 固定指向 `D:\Harumakigohan`，仓库放在其他位置时改成检出目录。

界面分绘制、贴纸、提取、蒙版、图层五个面板；背面成品从「导出 PNG」写入 `postcards/_workbench/out/`。

## 素材来源与版权

- 插画与 MV 画面的版权归 はるまきごはん 及各发行方所有，此处仅作个人设计练习存档，不用于出版、商用或再分发。
- 各组逐一来源见 `postcards/<组>/SOURCES.md`，工作台素材见 `postcards/_workbench/SOURCES.md`。
- 参考 MV 单文件 38–1038 MB，超出 GitHub 单文件上限，未收录本仓库。
- 原始素材库（`video/`、`image/`）与下载清单不在本仓库。
