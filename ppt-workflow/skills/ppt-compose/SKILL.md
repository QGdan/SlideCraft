---
name: ppt-compose
description: "根据已批准的大纲和模板制作或修改可编辑 PPT，并保留对象映射；适用于执行排版与内容修改，不负责访谈、模板选型或最终质量签字。"
---

# PPT 制作与修改

接收theme-prepare输出时，按项目docs/主题选择与同稿对照.md将同一design-system的font/colors传入图表、关系图与frame预制，并用配套asset-style绑定任务素材，再交brief-compose。主题变化要重新预制和查看真实页面，不能只改最终背景而留下旧图表颜色。

image-chart可读取同页图片visual_id和chart_visual_id，分别从任务素材包绑定。图表先用compact-chart-prepare生成，按项目docs/图片与原生图表联合表达.md保留事实/原始顺序与独立来源；不把完整图表连同大结论缩小硬塞，也不能省掉第二项必需素材。

封面、章节、行动结尾、图片、原生关系与图表可用brief-compose统一读取大纲、任务素材包和布局选择。整页模板先按项目docs/封面章节与行动结尾.md用frame-prepare准备原生片段，随实际预览进入素材包，再组成整套；原页ID/主张/正文和对象映射保留。超容量、多必需视觉或不支持模板不能静默简化。

按项目docs/素材风格与图像叙事.md用asset-record保存实际素材操作、提示词、参考图片快照与选用观察，再进material-pack；retrieved/existing没有本次生成提示词，计划不能充作实际调用。image-story经page-prepare制作上图下文；trend-prepare增加绑定对应月份事实的原生注释带，不能伪造数据点像素锚定或因果事件。

正文适配可按项目docs/内容驱动布局与中文容量.md调用page-prepare，输出原生文字片段、源文位置与证据区域。用已有asset-place/chart-prepare绑定任务素材与事实图表，再editorial-build。超过锁定页数返回needs_input，不生成制作片段；不能丢文、缩字或擅自改批准页数。该配方限定微软雅黑与常规宽屏，其他模板继续实际适配。

关系图用relationship-prepare（归本Skill）读取大纲中的明确关系，生成步骤产出、单层层级或双方案对照的原生elements；按项目docs/内容关系与原生构图.md合并到本页并进入素材包/实际导图流程。editorial-build写真实分组与绑定连接符；不再接受diagram/smartart占位矩形。不能将普通原生组冒称SmartArt，复杂/分支结构不静默改画简单流程。

按项目docs/视觉优先的制作约定.md执行：主要精力用于内容、选材、模板和逐页视觉打磨。保留必要的文件/数据与实际页面检查，普通排版不反复跑大规模工程测试；页面仅保留必要的数据、来源和许可标注，工程声明留在内部记录。阶段审核优先展示真实效果。

独立编辑引擎走editorial-build --input <spec> --design <获批design-system.json> --node <node.exe> --out <新目录>，保留raw.pptx和normalization.json并检查规范化后的candidate.pptx。显式design生成对应原生布局名，不等于任意导入模板重建。直接调用engine/editorial_build.cjs属于底层原始输出，不能跳过包检查与既有导出缺陷处理。

按项目docs/大纲驱动与任务素材包.md将素材准备与正式制作分开。模板确定前仅执行下载、制图预制和material-pack子任务，整理到本次任务素材目录，不提前生产整套成品。模板/最终素材包获批后，依详细大纲逐页制作，使用包内preparation和原生图表源；每页导图自查再继续。图片须与获批包的页、来源和字节一致，缺素材返回准备步骤；新增视觉来源可以登记，事实及原证据来源不得改动。

按项目docs/在线素材检索与入页.md执行asset-fetch和asset-place，将选定在线素材下载校验/缓存，再按明确页ID、对象ID、rect、contain/cover与focus合并到新spec。CC BY提供可见署名区，备注保留完整来源及处理说明。检查placement.json的重叠/PPI警告，编译并在目标软件查看真实页面；原文件不变。SVG另存不代表PPT原生形状。

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责按已批准的大纲和模板完成可编辑成品。阶段入口为 `compose`；底层命令 plan / build / revise 归本 Skill 所有。

## 制作

图表页可按项目docs/原生图表视觉配方.md执行chart-prepare：用获批事实表、来源、比较口径及事实模板结论准备原生chart与说明片段，保留fact_ids/text_template。它不自动编故事或批准数据。原始生产PPT保留完整工作簿；本机WPS转存可能丢嵌入工作簿，wps-template的chart-preservation失败时保留诊断副本并改走PowerPoint原件路线，不交付该WPS副本。

按项目docs/插画与原生模块库.md，asset-prepare可准备peeps人物插画，保持原色、原比例并保留SVG与CC0；模块用module-prepare输出原生elements片段。合并到对应页时核对source_refs已在本任务登记、对象ID不冲突、区域在画布内，再用完整deck检查和实际导图复核。模块预览含独立人物图片，不得把整页预览当可编辑模块；示例日期/措辞不能直接当本任务事实。模块容量不足要换构图或拆分，不缩字凑页。

本地Tabler图标选用后按项目 `docs/素材库使用.md` 执行asset-prepare，显式传库ID、页/对象ID、颜色与选用理由。输出透明PNG、SVG源、MIT许可和preparation.json；将其中asset/source片段按现有合同登记，source去重并在页面引用，再安排rect与contain。PNG是可替换图片，不能宣称原生图形可编辑。图片检索用asset-search --type all；未接入的其他库不能冒称可调用。

批量排版前先完成图表与素材准备清单.md，继承大纲数据与模板风格，整理选定图片、图表/关系图源文件及真实预览，查看后再进入成品制作。每页须有文字和相关视觉表达，纯段落页需要重组；不能只用装饰图标凑图。图表依本任务真实数据制作，无数据则采用有资料依据的关系/概念表达。资料或主张变更按原阶段退回，准备清单随本阶段交接，不能伪造新的审核通过。

按绑定项目 `docs/页内排版与素材调用工作流.md` 落实逐页内部排版，沿用常规画布与批准模板。读取page-visual-plan.md；没有时依据获批大纲补齐。对有图片/图标需求的页实际检索本地库，保存候选结果与选用理由，再登记来源、asset_id和放置方式；不得仅因存在素材库而宣称已调用。缺口通过有权使用的外部素材、可用生图工具或原生元素补足。自制原生图表/图形记录数据和制作来源，真实数据保持原生图表。维护使用记录与对象对应，不能将不相关配图或单一重复布局铺满全套。

先执行capabilities查看编译器真实支持边界。0.2合同新增横条/柱/折线、多类别/多系列和重点标注，仍需按[扩展图表合同](references/chart-v02.md)选择图型、尺度与数据绑定。编译/对象检查通过不表示本机Office渲染和编辑往返已验证。不支持的图型必须明确报错，不得统一改画横条或截图交付。

读取获批的需求、content-outline.json、template-selection.json 和实际模板。将大纲写为 deck-spec，沿用来源与事实 ID、逐页 ID 和已批准主张。不要在填内容时重新选模板，不能因为引擎不支持而静默换成另一种图表或版式。

在项目中使用 CLI 的 doctor 确认运行条件，再执行 plan/build；这里 plan 是构建输入冻结，不是叙事大纲。当前 PptxGenJS + MCP→Office 支持 unified-v3 的 8–20 页、单系列两类别横条图、三列表格和流程。其他模板或图表须真实适配并验证，不能只改配置声称支持。

文字、普通图表、表格和流程使用原生对象。AI 插画作为登记素材，记录路径、来源、许可和提示词。图片结构需编辑时可语义重建为原生形状/SVG，说明近似范围。使用 Figma 时按可用插件 Skill 操作并保存节点映射；没有真实导出与复核，不声称在线修改已同步回 PPTX。

使用 WPS 组件制作页面时，按 [WPS原生元素实测路线](references/wps-elements.md)选择已验证方法：原生形状/文本与组合复制、绑定连接符、表格、模板图表模块，以及内置 SmartArt 基本流程。创建、保存和重开分别核对；本机直接 AddChart、Shape.Duplicate 保存副本和部分 SmartArt 样式接口存在问题，不将枚举成功或返回句柄当作完成。不把这些局部能力等同于主构建引擎已支持任意元素。

新增场景蓝图构建与cover/contain图片适配，按[图片与蓝图路线](references/scene-images.md)执行。此独立编译器不等于旧plan/build支持任意新模板；实际资料与模板批准仍需继承。

## 修改

先定位要改的页、element ID 和原因。事实、口径和核心主张变化退回 ppt-outline；品牌与模板变化退回 ppt-template。得到相应批准后重建下游，不沿用旧审核。

底层 revise 仅支持实际 QA 定位的正文框原位置小幅扩大，最多两轮，不是任意文字重写器。其他已授权内容修改通过更新 spec、新建构建任务完成。保留旧版本，避免接管用户现有 Office 会话或删除不明隔离锁。

## 输出与交接

本机若Python启动的PowerPoint导图失败，按项目docs/Office直接导图与连接恢复.md使用直接PowerShell备用入口；WPS激活失败先执行一次只读激活，再以新目录重试MCP一次。两端保存、导图和回读按实际结果记录，不改注册表或接管用户会话；重试仍失败则保留未验证状态。

WPS 既有模板改稿可使用 wps-template MCP 路径，按获批模板的页号和形状 ID 提交带 expected 原文校验的修改清单，只写独立副本。此路径支持保留原生模板与选定页上的文字修改、保存和导图，不表示统一构建引擎支持任意新布局或任意图表数据编辑。核对 wps-template.json、独立进程 wps-readback.json、图表数据和逐页图像；不 Quit 共享 WPS、不改用户其他文稿。

composition.json 包含 deck、deck_spec、implementation_notes，可附 run_path、对象映射和修改记录的真实路径。输出 PPT 的文字、图表缓存与工作簿、表格和流程应与 spec 一致；资料、主张、版式必须匹配上游批准件。

执行 `compose --workspace <任务目录> --input composition.json` 提交，审核后交给 ppt-polish。底层构建命令和有限修复格式见本 Skill 的 references/engine-cli.md。这里完成制作，不给最终视觉质量签字。

