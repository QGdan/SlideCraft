# 生态调研汇报（14 页）

配套报告：`../01-研究报告/自动化PPT开源生态全景_20261017.md`

## 产物

| 文件 | 说明 |
|---|---|
| `生态调研汇报-20261017.pptx` | 14 页，16:9，微软雅黑 |
| `make_eco_deck.js` | PptxGenJS 生成源；设计 token 集中在文件头 |
| `rendered/slide-01..14.png` | PowerPoint COM 原生渲染，1600×900 |
| `rendered/contact-01..03.png` | 接触表，6 页/张 |
| `check_layout.py` | 文本框重叠 / 越界检查（补 linter 盲区，位于 `../04-核查证据/`） |
| `pixel_check.py` | 渲染图内容边界 / 三分区墨量检查（位于 `../04-核查证据/`） |
| `measure_text_bounds.ps1` | 用 PowerPoint 自身的 `BoundHeight/BoundWidth` 测真实文字溢出（位于 `../04-核查证据/`） |
| `text-bounds.json` | 上述测量的结果（本次为 `[]`，0 处溢出，位于 `../04-核查证据/`） |

## 复现

```powershell
$env:NODE_PATH="C:\Users\郭卓然\Desktop\项目\PPT-高质量生成研究\ppt-workflow\node_modules"
node make_eco_deck.js

python ..\..\02-工具链\deck_lint.py 生态调研汇报-20261017.pptx
python ..\..\02-工具链\deck_tools.py check 生态调研汇报-20261017.pptx
python ..\..\02-工具链\deck_tools.py render 生态调研汇报-20261017.pptx rendered --width 1600 --height 900
python ..\04-核查证据\check_layout.py 生态调研汇报-20261017.pptx
python ..\04-核查证据\pixel_check.py rendered
python ..\..\02-工具链\balance_check.py rendered
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\04-核查证据\measure_text_bounds.ps1 -Pptx 生态调研汇报-20261017.pptx -Out ..\04-核查证据\text-bounds.json
python ..\..\02-工具链\deck_tools.py sheets rendered --prefix contact --per-sheet 6
```

## 本次验收结果（2026-10-17）

| 检查 | 结果 |
|---|---|
| `deck_lint.py` | 14 slides，**0 error / 0 warning** |
| `deck_tools.py check` | OK，14 个 slide part |
| `check_layout.py` | 0 个文本框重叠 / 越界 |
| `measure_text_bounds.ps1` | 14 页、0 处真实文字溢出（一次完整运行；COM 偶发 RPC 错误时重试） |
| PowerPoint COM 渲染 | 14/14 页成功，1600×900 |
| `balance_check.py` | 底部留白 5.9–6.1%（页脚区），无异常大空洞 |
| `pixel_check.py` | 内容边界左/右 0.72in、下 0.43in，无边缘裁切 |

> 说明：这些是几何/像素级检查，不等于审美验收。正式使用前仍需人眼逐页看接触表，重点看断行、孤字、视觉重心与图表标签。
