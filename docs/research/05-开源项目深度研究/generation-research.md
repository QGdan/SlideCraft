# PPT 生成框架与端到端项目研究

研究日期：2026-10-13。范围：6 个项目；只读取官方仓库、源码、许可证和官方文档，未安装、未运行外部代码、未生成测试 PPTX。以下是静态选型结果，不是实测质量排名。

## 结论与建议

建议以 **PptxGenJS 作为新建原生可编辑页面的基座，python-pptx 作为已有 PPTX 模板读取、占位符填充和检查工具**。两者是确定性底层库，需要自己配置叙事、布局与渲染验收；不能把库本身当成设计智能体。

主线保留现有 **PptxGenJS + 补强 QA**；现有 PPTX 模板通路优先试验 **pptx-automizer**。**PPT Master（受约束 SVG → DrawingML）** 与 **PPTAgent 当前 skill（HTML → PPTX + 双重视觉验收）**作为对照。Presenton 适合需要浏览器编辑器/API 的独立平台，但导出核心的源码与许可证溯源尚未闭环，应先通过该门槛再考虑接入。上述排序是针对本地 coding-agent 工作流的工程判断，尚需统一测试集验证。

## 证据等级

- **A：直接证据**：已查看 LICENSE、依赖声明、核心实现入口或具体实现代码；足以判断该文件声明/实现的事项。
- **B：官方文档证据**：官方使用文档、技术设计、版本发布记录；能力边界较可信，但不等同实际运行成功。
- **C：项目自述**：README、营销演示、发布者声称；需要样本验证。
- **D：工程推断/待验证**：结合实现推断的适配风险；不能作为已确认缺陷。

所有 main/master 链接都是本次检索时状态；部署前须固定 commit、包版本和依赖锁，保存 LICENSE/NOTICE。已读取发布页的可追踪短提交：PptxGenJS v4.0.1 为 `3c9ec1b`，Presenton v0.9.11-beta 为 `e33a91b`，Presenton export v1.0.34 为 `c037536`；本次源码读取仍来自 main/master，因此不能把发布提交与当前源码完全等同。网页缓存与 release 页面有时只显示月日，本报告不擅自补全年份。根仓库许可证与模型权重、图片、字体、依赖许可证分别审查；“代码可见”不能直接写成“开源”。

## 选型总表

| 项目 | 类型与已核对许可证 | 编辑性与模板方式 | 部署/维护证据 | 本研究建议 |
|---|---|---|---|---|
| PptxGenJS | JS/TS 生成库；MIT，A | 原生文本、形状、表格、图表；代码定义 master/layout；无已确认任意 PPTX 导入编辑 API | package/source 4.0.1；Node 或浏览器；release 包含修复记录 | 主基座 |
| python-pptx | Python OOXML 库；MIT，A | 开已有 PPTX；继承其 master/layout；原生文本/表/图；跨文件复制复杂 | Python ≥3.8；HISTORY 顶部 1.0.2，2024-08-07；发行节奏较慢 | 模板与后处理 |
| PPTAgent | 研究框架已演进为 skill；MIT 根仓，A | 当前 HTML 源与可编辑转换；论文模板复用要查历史 tag | main skill；Linux/WSL/macOS；uv、Node、Playwright、LibreOffice | QA 编排参考/试验 |
| PPT Master | coding-agent 工作流 + SVG 编译器；MIT 根仓，A | 项目受约束 SVG 转原生 DrawingML；已有 PPTX 有专用 round-trip 路线 | 有 Windows 文档；Python 依赖多且版本下限为主；主要单维护者 | 原生对象路线优先试验 |
| pptx-automizer | Node 模板库；MIT，A | 导入现有 PPTX、复制 master/layout/图表关系；支持 PptxGenJS 动态对象 | package 0.9.3；CHANGELOG 0.9.4（2026-09-28），需核对实际发行；Node ≥20 | 模板通路优先 POC |
| Presenton | Web/Electron/API 应用；主仓 Apache-2.0，A；导出核心许可待闭环 | 自述有编辑器、PPTX 导入模板、editable export；底层外置 release 包 | 主仓 0.9.11-beta；发布 PR 记录活跃；Python/Node/Chromium/OCR 等 | 许可核验后独立试点 |

## 1. PptxGenJS

**直接核对。** [LICENSE](https://github.com/gitbrent/PptxGenJS/blob/master/LICENSE) 是 MIT；[package.json](https://github.com/gitbrent/PptxGenJS/blob/master/package.json) 为 4.0.1，真实声明 jszip、image-size、https 等依赖，因此 README 的“zero runtime dependencies”不能照抄为依赖事实。 [pptxgen.ts](https://github.com/gitbrent/PptxGenJS/blob/master/src/pptxgen.ts) 可以看到创建 slide/master/layout、ZIP OOXML 输出和图表工作簿生成调用，属于 A 级实现证据。

**编辑性。** 原生 addText/addShape/addTable/addChart 路线适合文字与数据需要后续修改的交付；作为图片插入的 SVG/照片不会自动变成可逐元素编辑的原生对象。库能统一主题/master，但仍须自己计算位置、留白、密度和文本框。HTML tableToSlides 是表格转换，不能等同任意网页/CSS 转换。能力总览以[官方仓库](https://github.com/gitbrent/PptxGenJS)为 B/C 级；具体输出需验收。

**模板复用与局限。** 已核对公开主类主要是创建/输出 API，未确认加载任意现有 .pptx 的 API。工程上应重建品牌 token 和代码 master，不能承诺无损读取单位模板（D）。布局自控是优势，但也意味着不会自动解决中文字体回退、字宽和长表分页。 [releases](https://github.com/gitbrent/PptxGenJS/releases) 的 4.0.1 修复包含表格自动分页超链接导致 repair；历史修复说明生产验收应包含 PowerPoint 打开检查。

**待验证。** 用固定中文字体、长中英标题、原生组合图、跨页表格，验证 PowerPoint/LibreOffice 的换行一致性和编辑能力。PptxGenJS 本身不提供完整 PPTX 视觉渲染链，另配渲染器与截图审查。

## 2. python-pptx

[LICENSE](https://github.com/scanny/python-pptx/blob/master/LICENSE) 是 MIT；[pyproject.toml](https://github.com/scanny/python-pptx/blob/master/pyproject.toml) 声明 Python ≥3.8，Pillow/lxml/XlsxWriter/typing_extensions。 [presentation.py](https://github.com/scanny/python-pptx/blob/master/src/pptx/presentation.py) 确认保存、master/layout 集合及尺寸读写，属于 A 级。

官方[Working with Presentations](https://python-pptx.readthedocs.io/en/latest/user/presentations.html)说明可读取已有 PPTX；[Working with Slides](https://python-pptx.readthedocs.io/en/latest/user/slides.html)说明新增 slide 继承 layout/master，并提醒模板布局索引不保证统一。这个路线比“截图仿制模板”更适合固定企业/学院样式（推断）。[charts 文档](https://python-pptx.readthedocs.io/en/latest/user/charts.html)说明原生图表与数据接口，可作为可编辑图表生成依据。

官方部分 user 文档内容明显历史化：例如 presentations 页仍有 Notes Pages 不可操作的旧叙述，而当前代码存在 notes_master；不能把旧文档的每条限制视为最新事实。应以当前 API/源码核对。跨 presentation 通用复制、复杂 SmartArt/动画编辑与未知 OOXML 往返不能直接承诺。 [HISTORY](https://github.com/scanny/python-pptx/blob/master/HISTORY.rst) 顶部明确 1.0.2（2024-08-07）；这是可核实的最后记录，不能据此单独断言停止维护。

建议只用稳定公开接口填充占位符、添加原生对象和做 XML 检查，避免无约束地把 XML hack 堆成核心编排。待验证含多 master、图表嵌入工作簿、图片裁切、已有动画的“打开—保存”回归；导入无损与“能操作所有对象”是两个不同验收项。

## 3. PPTAgent：必须分三条版本路线

[根仓 README](https://github.com/icip-cas/PPTAgent)明确：EMNLP 2025 论文复现使用 **v0.2.0**；DeepPresenter/ACL 2026 使用 **v1.1.38**；当前 main 为 **skills/pptagent**。 [v0.2.0 README](https://github.com/icip-cas/PPTAgent/blob/v0.2.0/README.md)、[v1.1.38 README](https://github.com/icip-cas/PPTAgent/blob/v1.1.38/README.md)是历史复现入口，不能混用 main 安装流程、研究基准与历史模板能力。根仓 [LICENSE](https://github.com/icip-cas/PPTAgent/blob/main/LICENSE) 是 MIT（A）。

当前 [SKILL.md](https://github.com/icip-cas/PPTAgent/blob/main/skills/pptagent/SKILL.md)由宿主 agent 研究与写 HTML，工具负责渲染、转换与交付核验；存在 review-slides → build → review-deck → finalize 流程。 [scripts/pptagent.py](https://github.com/icip-cas/PPTAgent/blob/main/skills/pptagent/scripts/pptagent.py) 的 doctor 真正检查 Node、LibreOffice、Chromium、Python/Node Playwright 匹配，以及 deeppresenter/html2pptx_cli.js（A）。并非“只装一段提示词就能跑”。

[requirements.txt](https://github.com/icip-cas/PPTAgent/blob/main/skills/pptagent/requirements.txt)固定 pptagent==1.1.37、playwright==1.62.0，并列 PyMuPDF、fastmcp 等。这是 **main skill 依赖的转换运行时版本**，不是让研究复现一律用 1.1.37。Windows 环境应走 WSL2/Linux 测试；README 支持范围为 Linux/WSL/macOS，不能把 POSIX 命令直接贴成 Windows 原生安装承诺。

[task-contract.md](https://github.com/icip-cas/PPTAgent/blob/main/skills/pptagent/references/task-contract.md) 明确 static HTML/CSS、固定画布、本地资源、显式文本宽度；还明确中英文字度量在 PPTX 后会改变，必须复审导出文件（B）。建议借鉴“源和导出分别审、修改使旧审查失效”的机制，不直接用论文评分当本地质量保证。模板保真与数据图表对象性仍要按当前转换器检验。

## 4. PPT Master

[LICENSE](https://github.com/hugohe3/ppt-master/blob/main/LICENSE)为 MIT。 [technical-design.md](https://github.com/hugohe3/ppt-master/blob/main/docs/technical-design.md)将 SVG 定义为项目受约束中间语言，非任意 SVG 转换器；原生图表/表格有显式变体，默认图示由 DrawingML 图形组成。视觉自查在该技术文档中是 opt-in，采用到本地高质量工作流时，应由用户授权范围内的自有流程强制渲染验收。

已核对实际编译路径： [svg_to_pptx.py](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/svg_to_pptx.py)包装入口 → [__init__.py](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/svg_to_pptx/__init__.py) → [drawingml/converter.py](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/svg_to_pptx/drawingml/converter.py)、[pptx_package/builder.py](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py)。converter 直接导入 text/path/group/shape 转换并校验原生替换 metadata；对不支持状态抛错误，可证实不是简单整页贴图（A）。但照片仍为图片；原生对象不保证数据图表已经是 Office chart。

模板与编辑分专门路由：新建使用受约束 SVG 设计，导入编辑用 round-trip 恢复不变源对象；这比单一“读模板—生成”复杂。 [Windows 文档](https://github.com/hugohe3/ppt-master/blob/main/docs/zh/windows-installation.md)存在，可作为本地试验入口（B）。 [完整 requirements](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/requirements.txt)包含 python-pptx/XlsxWriter/skia-pathops/uharfbuzz 及许多可选转换、TTS、图像依赖；大量采用 >=，需要自行锁版本。PyMuPDF 明确为 AGPL-3.0、仅 PDF 转换使用；根仓 MIT 不能替它授权。

维护判断：当前技术设计与模块结构提供明确质量契约，README 自述主要由一人维护；不根据 star 数做稳定性结论。建议优先作为 SVG→原生 PPTX 可编辑路线的 POC，但部署前只读审查安装器/更新器，固定 commit。待验证：复杂路径、公式、native chart 开关、模板 round-trip、图形数量激增时编辑便利性；真实 Office 渲染与 SVG 预览不一致需回到导出验收。

## 5. pptx-automizer：补齐已有 PPTX 模板通路

**主结论。** MIT 的 Node 模板库，适合从已设计 PPTX 复制页面/对象并填充文字、图表和表格，同时调用 PptxGenJS 添加动态内容。已核对代码有相关部件复制与 notes 关系重映射，可作为模板通路优先试验；不保证任意模板无损。package 为 0.9.3，但 CHANGELOG 顶部 0.9.4（2026-09-28），部署要先消除版本差异。动画不在支持范围，复杂布局与图表需真实 PowerPoint 验收。

**A 级证据。** [LICENSE](https://github.com/singerla/pptx-automizer/blob/main/LICENSE)是 MIT；[package.json](https://github.com/singerla/pptx-automizer/blob/main/package.json)要求 Node ≥20，依赖 @xmldom/xmldom、JSZip 和 **PptxGenJS ^3.12.0**，不能默认与主线 4.0.1 API 完全一致。[automizer.ts](https://github.com/singerla/pptx-automizer/blob/main/src/automizer.ts)实现 loadRoot/load/addSlide/addMaster，且 autoImportSlideMasters 会调用源布局。[related-content-copier.ts](https://github.com/singerla/pptx-automizer/blob/main/src/classes/related-content-copier.ts)显式复制 chart/image/diagram/OLE/hyperlink；[slide-notes-copier.ts](https://github.com/singerla/pptx-automizer/blob/main/src/classes/slide-notes-copier.ts)复制 notes 与双向 relationship。这是 OOXML 部件复用的代码证据，不能据此替每个模板背书。

**B 级与版本边界。** [charts 文档](https://singerla.github.io/pptx-automizer/charts)提供 native chart 修改和 embedded workbook 读取接口；[master/layout 文档](https://singerla.github.io/pptx-automizer/masters-layouts)说明导入母版及关联布局，但 complex layout 内容存在限制。该文档与 CHANGELOG 的 0.9.3 OLE/image 修复存在局部不同步迹象，应按具体 case 回归。[limitations](https://singerla.github.io/pptx-automizer/limitations)明确 animations out of scope、增删形状可能破坏 animation id，extended charts 部分属性缺 modifiers，当前测试聚焦 PowerPoint 2019。[CHANGELOG](https://github.com/singerla/pptx-automizer/blob/main/CHANGELOG.md)明确 0.9.2 deprecated、0.9.3 补 image/OLE 关系修复，0.9.4 补 dangling chart content-types/SVG/table 修复；这些是维护与可靠性证据，也是必须锁版本的理由。

**待验证。** 挑选实际学院模板，测试多母版、中文字体、原生组合图与数据工作簿、超链接、notes、图像关系；创建对象命名/creationId 槽位规范。比较仅复制、改文字、改图表、增加对象四组输出。建议模板中的动画先保留隔离样例，不让包含动画的模板成为默认稳定通路；检查 relationships、content-types 与实际 Office 编辑数据结果。不要使用 deprecated 0.9.2。

补充筛查：dom-to-pptx 未列入六项主选。它的 [LICENSE](https://github.com/atharva9167j/dom-to-pptx/blob/master/LICENSE)是 MIT，package 2.1.2、CHANGELOG 2026-09-14；[src/index.js](https://github.com/atharva9167j/dom-to-pptx/blob/master/src/index.js)有 html2canvas 局部截图，[SUPPORTED.md](https://github.com/atharva9167j/dom-to-pptx/blob/master/SUPPORTED.md)明确 blur/CORS/动画限制。“完全可编辑”需逐对象验证，仅保留为 HTML 对照备选。

## 6. Presenton

[主仓 LICENSE](https://github.com/presenton/presenton/blob/main/LICENSE)实为 Apache-2.0； [README](https://github.com/presenton/presenton)提供 Web/Electron、BYOK、本地模型、API、已有 PPTX 设计导入与编辑器自述，属于 B/C。slides_markdown 仍经 LLM 选布局和字段映射，不是确定性 Markdown 渲染；自述每项默认 100 词、最多 50 项，长文本可能截断。应注意 source copy 的事实完整性。

[Dockerfile](https://github.com/presenton/presenton/blob/main/Dockerfile)实际为 Python 3.11 + Node 22、Next.js/FastAPI、Chromium、Noto CJK 字体、LiteParse、可选 Tesseract、模型/图标缓存等；不是轻量纯 Python app（A）。 [package.json](https://github.com/presenton/presenton/blob/main/package.json)为 0.9.11-beta；[releases](https://github.com/presenton/presenton/releases)含模板、迁移、离线与导出修复的具体 PR 记录，支持活跃但仍 beta 的判断。

**关键未闭环事项。** package 将 presentationExportVersion 固定为 v1.0.34。 [sync-presentation-export.cjs](https://github.com/presenton/presenton/blob/main/scripts/sync-presentation-export.cjs)从独立仓库 release 下载 `presenton-export-core-opensource-1.0.34.tgz` 并安装 `@presenton/export-core`。 [export 仓库](https://github.com/presenton/presenton-export)本次浏览只有 README、一个 commit；[release v1.0.34](https://github.com/presenton/presenton-export/releases/tag/v1.0.34)自称 open-source core，但本次没有解包读取其许可证、源码、源码映射、NOTICE 和可复现构建。本报告不能认定它是闭源/受限许可，也不能认定主仓 Apache 自动覆盖该 tgz；状态应写 **“主应用开源已核对；导出核心许可证与完整源码待核验”**，不是贸然贴 source-available 标签。

建议试装前先静态核验固定版本 tgz 的 package.json/LICENSE/NOTICE 与源码获取位置、哈希和第三方许可证，再用 Docker 固定镜像 digest、做网络访问盘点。其导入模板实际样式保真、文本原生性、native chart/table、编辑器与导出差异、local LLM 是否支持所需 structured output，都要在相同测试集测试。

## 可执行的审核后 POC 计划

此处仅为批准后执行清单；本次没有安装或运行。

1. **先锁对象标准。** 10 页中文学术/答辩测试集：封面、长标题、中英段落、双栏、流程图、原生柱线图、数据表、公式、图片裁切、带 master 的现有模板。数据与来源固定，避免以内容不同解释视觉差异。
2. **最小环境分两条。** Windows 原生用于 PptxGenJS/python-pptx/PPT Master；WSL2 或容器用于 PPTAgent/Presenton。pptx-automizer 另锁自身 PptxGenJS 3.x 依赖。不要一次全局安装六套。
3. **先跑两基座与两端到端。** PptxGenJS 和 python-pptx 给确定性基线；pptx-automizer 先制作模板基线，PPT Master 和 PPTAgent 再作同数据对照；Presenton 要先完成 export-core 溯源。
4. **双重验收。** 检查 PPTX ZIP 的 `<p:sp>`/`<a:t>`、chart/table parts、embedded workbooks、图片数、外部关系；再在真实 PowerPoint 渲染并编辑抽检，LibreOffice 只作第二渲染器。文本存在于 XML 不能单独证明视觉正确，矢量路径图表也不能冒充数据图表。
5. **评估与停线。** 文字零裁切/无遮挡、图表数据与来源一致、所有指定对象能编辑、模板关键位置与字体满足误差阈值、源与导出复审通过；记录耗时、重试、模型/token、人工修复分钟、失败页率和可编辑覆盖率。任一关键对象被整页截图替代或内容被截断，直接标为未通过。
6. **产物契约。** 每次保存原始素材、结构化内容、布局源、生成脚本、锁文件/commit/LICENSE/NOTICE、PPTX、PDF/页图与质量报告。只在审核后选择一条主路径接入个人 skill，另外保留一种输出回退。

## 尚未验证的共性问题

- 未做实际安装、生成、性能、成本或用户可编辑性实测；本报告不存在“已运行成功”的断言。
- GitHub API 经本地 PowerShell 网络读取失败；维护时间以浏览工具读取的官方 HISTORY/CHANGELOG/Release 为准，没有 fabricated pushed_at。
- 所有外部库、技能、模型权重、图标和字体都需独立 SBOM；本次六个根仓许可证都是 MIT/Apache 的明确授权（Presenton 导出核心例外未闭环），没有把可见源码的受限许可项目包装成 OSI 开源。
- PPTAgent 的论文结果、PPT Master 的示例、Presenton 的营销预览和库星数均未当作统一质量排名依据。

