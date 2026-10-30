# 核查证据

本目录保存 2026-10-17 对汇报 PPT 与调研包的可复核检查结果。所有检查都是**几何/像素/结构级**，不等于审美验收。

| 文件 | 内容 | 结论 |
|---|---|---|
| `deck-lint.txt` | `deck_lint.py` 静态检查 | 14 页，0 error / 0 warning |
| `package-check.txt` | `deck_tools.py check` 包结构 | OK，14 个 slide part |
| `layout-check.txt` | `check_layout.py` 文本框重叠/越界 | 0 个问题 |
| `pixel-check.txt` | `pixel_check.py` 渲染图边界/墨量 | 左右 0.72in、下 0.43in，无裁切 |
| `balance-check.txt` | `balance_check.py` 垂直平衡 | 底部留白 5.9–6.1%（页脚区） |
| `text-bounds.json` | PowerPoint COM `BoundHeight/BoundWidth` | `[]`，0 处溢出 |
| `SHA256SUMS.txt` | 主要产物的 SHA256 | 用于绑定版本 |

## 复跑

```powershell
cd ..\03-汇报PPT
python ..\..\02-工具链\deck_lint.py 生态调研汇报-20261017.pptx
python ..\..\02-工具链\deck_tools.py check 生态调研汇报-20261017.pptx
python ..\04-核查证据\check_layout.py 生态调研汇报-20261017.pptx
python ..\04-核查证据\pixel_check.py rendered
python ..\..\02-工具链\balance_check.py rendered
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\04-核查证据\measure_text_bounds.ps1 -Pptx 生态调研汇报-20261017.pptx -Out ..\04-核查证据\text-bounds.json
```

## 注意

- `measure_text_bounds.ps1` 依赖本机 PowerPoint COM；重复自动化时偶发 `RPC server is unavailable`，重开 PowerPoint/重试即可。`text-bounds.json` 为一次完整运行的结果。
- `pixel_check.py` 的背景取左上角像素；封面左侧有全宽色条，因此左右边界显示 20px/1px 属预期。
- 这些脚本只检查“有没有明显坏掉”，不检查“好不好看”。正式交付前仍需人眼看接触表。
