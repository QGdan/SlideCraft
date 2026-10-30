# 第三方依赖记录（P0）

本阶段没有复制 OpenAI/JetBrains helper、Anthropic Skill 或其他候选项目代码。历史包源码仅作本地基线快照，不将其解释为新开源许可证授予。

- PptxGenJS：固定 4.0.1，通过 npm 安装；安装包 LICENSE 为 MIT。Node 传递依赖版本、许可证标记与 integrity 见 package-lock.json。
- Python 依赖：固定直接依赖和实际传递依赖；版本见 requirements.lock.txt，下载来源及包 hash 见 pip-install-report.json。
- 安装的 Python 包许可证路径/hash、Node 包声明和字体路径/hash，见上级 `06-实施与阶段审核/P0/dependencies.json`。缺失的许可证字段表示没有取得该字段，不能推断无许可。
- 微软雅黑、Calibri、Arial：来自本机 Windows/Office 字体目录，仅做路径/hash 清单，不复制字体文件，不将其当作开放字体。
- PowerPoint：本机商业 Office 运行依赖；本地探测脚本不改变其许可或跨环境支持范围。

正式分发前在 P5 按具体包含的代码、依赖、素材生成完整 NOTICE/许可包；本文件是 P0 的依赖记录，不是“整个链路完全开源”的声明。

## P5 本地候选包

候选包包含35个Python wheel、19个Node tarball及对应固定hash/来源记录，许可证与声明汇总在 `licenses/dependency-inventory.json`。这些依赖通过原有安装记录的固定URL和hash取得，Node tarball经lockfile SHA512验证。isarray的MIT原文在其README，已收录；https1.0.0仅有package.json的ISC声明，下载包中未取得独立许可正文，保留为公开分发前待核项，不自行补写授权。

自有源码未由用户选定公开发布许可证，本次仅向用户交付本地研究候选包。包内概念图是本项目获用户授权的生成/修改素材，提示词与来源随附；未宣称拥有独占权、公开分发已审清或图片本身可编辑。未复制Office、Python、Node程序或Windows字体二进制。公开发布许可、完整质量门禁与真实模板兼容尚未全部完成。
# P2 视觉修订的可选 MCP 通路

项目独立 `.mcp-venv` 使用官方 `mcp==2.3.0`（MIT），通过本地 stdio 客户端调用自有 Office bridge。未修改主 `.venv` 依赖或全局客户端配置。实际传递依赖固定在 `office-mcp/requirements.lock.txt`，下载来源和 hash 记录在 `office-mcp-install-report.json`。`pywin32==312` 在此独立环境中用于真实 PowerPoint COM 自动化。此通路为项目自有实现，没有复制候选 MCP 仓库代码。

