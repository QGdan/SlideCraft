---
name: ppt-compose
description: "根据已批准的大纲和模板制作或修改可编辑 PPT，并保留对象映射；适用于执行排版与内容修改，不负责访谈、模板选型或最终质量签字。"
---

# PPT 制作与修改

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责按已批准的大纲和模板完成可编辑成品。阶段入口为 `compose`；底层命令 plan / build / revise 归本 Skill 所有。

## 制作

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

WPS 既有模板改稿可使用 wps-template MCP 路径，按获批模板的页号和形状 ID 提交带 expected 原文校验的修改清单，只写独立副本。此路径支持保留原生模板与选定页上的文字修改、保存和导图，不表示统一构建引擎支持任意新布局或任意图表数据编辑。核对 wps-template.json、独立进程 wps-readback.json、图表数据和逐页图像；不 Quit 共享 WPS、不改用户其他文稿。

composition.json 包含 deck、deck_spec、implementation_notes，可附 run_path、对象映射和修改记录的真实路径。输出 PPT 的文字、图表缓存与工作簿、表格和流程应与 spec 一致；资料、主张、版式必须匹配上游批准件。

执行 `compose --workspace <任务目录> --input composition.json` 提交，审核后交给 ppt-polish。底层构建命令和有限修复格式见本 Skill 的 references/engine-cli.md。这里完成制作，不给最终视觉质量签字。

