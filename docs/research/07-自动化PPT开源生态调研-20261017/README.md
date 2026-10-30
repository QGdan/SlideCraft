# 自动化高质量 PPT：开源生态、插件与工作流（2026-10-17）

本文件夹是“自动化制作高质量 PPT”专题的**完整交付包**：全景调研 + 选型建议 + 项目卡片 + 14 页汇报样例 + 可复核的检查证据。

> **一句话结论**：生态已经够用，缺的不是生成器，而是“**可编辑性口径 + 质量门 + 模板治理**”。

---

## 先看哪

| 你想做什么 | 打开 |
|---|---|
| 5 分钟了解结论与建议 | **[00-执行摘要.md](./00-执行摘要.md)** |
| 看完整调研（30 个项目、5 条路线、4 类插件、6 种工作流） | **[01-研究报告/自动化PPT开源生态全景_20261017.md](./01-研究报告/自动化PPT开源生态全景_20261017.md)** |
| 直接查某个项目 | [02-项目卡片/项目卡片.json](./02-项目卡片/项目卡片.json) 或 [.csv](./02-项目卡片/项目卡片.csv) |
| 看汇报样例 | **[03-汇报PPT/生态调研汇报-20261017.pptx](./03-汇报PPT/生态调研汇报-20261017.pptx)**；缩略图 [contact-01](./03-汇报PPT/rendered/contact-01.png) |
| 核对检查结果 | [04-核查证据/](./04-核查证据/) |
| 要落地：接入顺序、POC、90 天计划、风险 | **[05-建议与路线图.md](./05-建议与路线图.md)** |
| 查所有外链与证据等级 | [06-来源清单.md](./06-来源清单.md) |

---

## 文件夹结构

```
07-自动化PPT开源生态调研-20261017/
├── README.md                     ← 你在这里
├── 00-执行摘要.md                 ← 给决策者的一页半
├── 01-研究报告/
│   └── 自动化PPT开源生态全景_20261017.md
├── 02-项目卡片/
│   ├── 项目卡片.json              ← 机器可读（30 条）
│   ├── 项目卡片.csv               ← Excel/WPS 可直接打开
│   ├── build_catalog.py
│   └── export_csv.py
├── 03-汇报PPT/
│   ├── 生态调研汇报-20261017.pptx
│   ├── make_eco_deck.js
│   ├── README.md
│   └── rendered/                  ← 14 页 PNG + 3 张接触表
├── 04-核查证据/
│   ├── deck-lint.txt / package-check.txt / layout-check.txt
│   ├── pixel-check.txt / balance-check.txt / text-bounds.json
│   ├── check_layout.py / pixel_check.py / measure_text_bounds.ps1
│   └── SHA256SUMS.txt
├── 05-建议与路线图.md
├── 06-来源清单.md
└── 99-归档/                       ← 整理前的旧说明，仅留档
```

---

## 30 秒选型

| 场景 | 路线 | 代表工具 | 交付形态 |
|---|---|---|---|
| 10 页内技术分享 | W1 Markdown 极速线 | Marp、Slidev、reveal.js | HTML/PDF；可接受图片化 PPTX |
| 企业/学院品牌汇报 | W2 模板注入线 | pptx-automizer、python-pptx | 原生 PPTX（E4） |
| 学术答辩 | W2 学院模板 + 原生图表 | python-pptx、PptxGenJS | 原生 PPTX（E4） |
| 数据密集报告 | W2 + 原生 chart | PptxGenJS、模板 | 原生 PPTX（E4，数据可改） |
| 发布级视觉 | W3 设计系统线 | PPT Master、Slidev editable、自研 | PPTX（E3–E4，需逐页验回退） |
| 批量运营 | W5 平台/API 线 | Presenton API、n8n、Dify | PPTX（需审核队列） |
| 存量改造 | W6 提取→重排→回写 | python-pptx、pptx-automizer | 原生 PPTX（保内容/结构） |

> W1–W6 的完整定义、质量门与适用边界见 [01-研究报告 §6](./01-研究报告/自动化PPT开源生态全景_20261017.md#6-六种可落地工作流)；本表只给默认选择。

**三条硬建议**：

1. **先定 E 级别，再选路线**。要求 E4（原生图表 + 母版）却选 Marp 默认，是需求错配。
2. **模板优先**。企业/学院场景，模板注入在质量、成本、可编辑性三方面同时占优。
3. **不要平台化替换**。保持 PptxGenJS 主引擎与六阶段工作流，把外部项目当“零件”接入。

---

## 五个判断

1. **生态分五条路线**：原生库、标记语言、HTML/SVG 设计源、模板复用、Agent 端到端；不是替代关系，是质量/成本/可编辑性三角上的取舍。
2. **2026 年的分水岭是“可编辑 PPTX”从实验走向基线**：Slidev 有 `pptx-editable`，Marp 有实验性可编辑导出，PPT Master 用受约束 SVG 转 DrawingML，PPTAgent 转向 HTML + 双评审。
3. **质量是乘法**：内容 × 叙事 × 视觉 × 工程 × 运维；任一层为 0，整体为 0。`lint 0 error` 只覆盖工程层的一部分。
4. **Agent 的护城河是视觉回环与失败恢复**，不是文案生成；PPTAgent 的“源/导出分别审、修改使旧评审失效”最值得借鉴。
5. **插件层的正确抽象是四个原语**：`measure / render / lint / export`；34 个细碎 MCP 工具不如这四个稳定。

---

## 本次核查结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 汇报 PPT 静态检查 | 14 页，**0 error / 0 warning** | [deck-lint.txt](./04-核查证据/deck-lint.txt) |
| PPTX 包结构 | OK，14 个 slide part | [package-check.txt](./04-核查证据/package-check.txt) |
| 文本框重叠 / 越界 | 0 | [layout-check.txt](./04-核查证据/layout-check.txt) |
| PowerPoint 原生渲染 | 14/14 页，1600×900 | [rendered/](./03-汇报PPT/rendered/) |
| PowerPoint 文字边界 | 0 处溢出（`[]`） | [text-bounds.json](./04-核查证据/text-bounds.json) |
| 渲染内容边界 | 左右 0.72in、下 0.43in，无裁切 | [pixel-check.txt](./04-核查证据/pixel-check.txt) |
| 垂直平衡 | 底部留白 5.9–6.1%（页脚区），无异常空洞 | [balance-check.txt](./04-核查证据/balance-check.txt) |

> 这些是几何/像素级检查，**不等于审美验收**。正式使用前请人眼扫一遍 [接触表](./03-汇报PPT/rendered/contact-01.png)，重点看断行、孤字、视觉重心与图表标签。

---

## 研究边界

- **30 个项目/插件**（含 3 个评估基准）；未在本机安装或运行任何新候选项目，项目能力以 README/官方文档/源码入口为准。
- **星数是 2026-10-17 的 shields.io 快照**，只表示社区规模，不作为质量或稳定性排名。
- **许可证以仓库根目录为准**；`Presenton` 的 `@presenton/export-core`、`PPT Master` 可选依赖 `PyMuPDF`（AGPL）、字体/图片/模板素材均需单独核查。
- 本包**不改变** `05-开源项目深度研究/` 的 2026-10-13 选型结论与已审核的六阶段主方案；它补齐的是全景、插件层、工作流模式与接入映射。

---

## 复现

```powershell
# 1) 项目卡片（JSON）+ CSV
python .\02-项目卡片\build_catalog.py
python .\02-项目卡片\export_csv.py

# 2) 重新生成汇报 PPTX 并验收
cd .\03-汇报PPT
$env:NODE_PATH="C:\Users\郭卓然\Desktop\项目\PPT-高质量生成研究\ppt-workflow\node_modules"
node make_eco_deck.js
python ..\..\02-工具链\deck_lint.py 生态调研汇报-20261017.pptx
python ..\..\02-工具链\deck_tools.py check 生态调研汇报-20261017.pptx
python ..\04-核查证据\check_layout.py 生态调研汇报-20261017.pptx
python ..\..\02-工具链\deck_tools.py render 生态调研汇报-20261017.pptx rendered --width 1600 --height 900
python ..\04-核查证据\pixel_check.py rendered
python ..\..\02-工具链\balance_check.py rendered
python ..\..\02-工具链\deck_tools.py sheets rendered --prefix contact --per-sheet 6
```

`build_catalog.py` 只读内置的项目清单，不联网；CSV 使用 UTF-8 BOM，Excel/WPS 打开中文不乱码。
