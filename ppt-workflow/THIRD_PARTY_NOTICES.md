# 第三方依赖记录（P0）

2026-10-31 源码整理说明：下文是历史来源记录。历史安装包、演示与截图已清理，本源码包不附带当时的 vendor、安装报告、外部会员模板或上游源码快照；旧路径不代表包内文件存在。当前图标和插画所附 LICENSE、来源及哈希记录继续保留。未给整个项目新增开源许可证。

2026-10-19 Open Peeps人物子集：正式索引纳入2项，作者Pablo Stanley，官方https://www.openpeeps.com/明确CC0。SVG原件、CC0法律文本、官网许可快照、SHA256与检索元数据在assets/illustrations/；未虚构网站素材的Git提交。原生模块为本项目自有组件的复用/改进，未复制第三方模板代码；人物进入PPT时为PNG，SVG另存。

2026-10-19 Tabler图标子集：导入24项outline SVG与其渲染PNG，上游固定提交a4ce1404bc6d24d3c365afe7b258d6bf6f48d62d。MIT原文在assets/icons/tabler-outline/LICENSE，仓库/许可URL及哈希在provenance.json，逐图来源与哈希在assets/icons/library.json。中文标签由本项目整理；未复制Tabler Illustrations。运行时未新增依赖，预览由宿主已有sharp一次性渲染。

2026-10-18工程融合记录：新质量合同与校验器参考PPTAgent、PresentBench和PPT Master的公开工作流方法，由本项目重新实现，未复制这些框架代码或数据集。固定提交、根许可快照与原文哈希见项目10-项目自动化优化实施-20261018/upstreams；具体采用范围见docs/开源融合记录.md。PptxGenJS仍为原锁定依赖，automizer仍保留在隔离实验中，不宣称已增加为生产依赖。

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



2026-10-19方法研究：Presenton Skills、pptx-gen、Tahta、ImageGen PPTX Pipeline与Slidev官方主题，固定版本及许可快照保存在项目12-视觉模板深化-20261019/upstreams-host。本轮未复制其代码、Skill正文、模板或图标。新增蓝图和适配器为原创；场景PNG由宿主imagegen生成，来源与完整提示词在assets/campus-editorial-v1。Slidev主题的代码MIT与图片CC BY-NC-SA 4.0分开，不将根许可用于替代素材授权。
