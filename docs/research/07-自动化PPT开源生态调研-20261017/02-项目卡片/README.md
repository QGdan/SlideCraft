# 项目卡片

`项目卡片.json` 是本专题的机器可读底表，共 **30 条**，覆盖原生库、模板复用、标记语言、HTML/SVG、Agent、Skill/MCP、评估基准。

| 文件 | 说明 |
|---|---|
| `项目卡片.json` | 主数据；schema `ppt-oss-landscape/v1` |
| `项目卡片.csv` | 同内容，UTF-8 BOM，Excel/WPS 可直接打开 |
| `build_catalog.py` | 生成 JSON；内置清单，不联网 |
| `export_csv.py` | 从 JSON 导出 CSV |

## 字段

| 字段 | 含义 |
|---|---|
| `category` | 技术路线/形态（native-library、template-reuse、markup、agent、mcp…） |
| `license` | 仓库根目录许可证；子包/素材另计 |
| `stars` | 2026-10-17 shields.io 快照，仅表示社区规模 |
| `output` | 主要产物（pptx / pdf / html / png…） |
| `editability` | 本报告定义的 E0–E4 可编辑级别 |
| `role` | 在本项目中的建议角色（primary-engine、template-channel…） |
| `strengths` / `limits` | 强项与边界（来自 README/文档/源码入口） |
| `evidence` | A=源码/许可直读；B=官方文档；C=README/演示；D=推断 |

## 注意

- 星数**不是**质量或稳定性排名。
- 同一项目的不同分支/镜像不重复计数。
- `Presenton` 的导出核心是独立 release 包，许可与源码未闭环；`PPT Master` 的可选 PDF 依赖 PyMuPDF 为 AGPL。
- 改动清单后请同时重跑 `build_catalog.py` 与 `export_csv.py`，并更新 `04-核查证据/SHA256SUMS.txt`。
