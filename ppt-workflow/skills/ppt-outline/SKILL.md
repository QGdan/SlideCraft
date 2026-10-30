---
name: ppt-outline
description: "整理、核对 PPT 资料和事实来源，设计叙事与逐页大纲；适用于已有需求后研究内容，不负责模板绘制或成品视觉审核。"
---

# PPT 资料与大纲

同页图片与图表可分别列为两项required视觉任务，说明各自证据作用及如何支持同一主张；不要合并为一个无来源的装饰任务。可用dominant_evidence标明重点，按docs/图片与原生图表联合表达.md交给模板选择组合。

图片/图标任务可按项目docs/素材风格与图像叙事.md补visual_direction，明确用途角色、主体、媒介、画幅、留白、fit与避开内容。证据照片与场景/概念图分开，不用生成图替代真实证据；全套风格由模板Skill确定。 封面、章节与行动结尾可按docs/封面章节与行动结尾.md写editorial_frame，声明页面角色和已写好的标签；原文仍在body_blocks，字体、颜色和坐标留给模板/制作。

实际正文是模板容量判断的输入。按项目docs/内容驱动布局与中文容量.md给出有序正文块与证据类型；页数受限时明确标记，正文改写和叙事拆页由本阶段决定。模板Skill可以比较布局，不得静默删除已批准内容。

关系/流程页按项目docs/内容关系与原生构图.md，在详细brief的diagram视觉任务中写relationship：关系类型、原文依据、来源、节点与边；对照页写共同维度和两侧内容。可补reading_order、dominant_evidence、layout_reason。只确定信息关系，不写几何坐标；无法从资料证明的关系不能为画图而虚构。

新任务按项目docs/大纲驱动与任务素材包.md编写production-brief.json并用production_brief指向它。与content-outline逐页ID/顺序/主张一致；写实际正文body_blocks、speaker_notes及每项visuals的用途、检索词、构图倾向、引用和必需标记。连同quality_plan一起审核内容深度和论证，不只写目录。大纲获批后按这些需求备齐素材，模板选型仍归ppt-template。

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责“讲什么、凭什么、怎么讲”。入口命令为 `outline`；读取已批准的 requirements.json，输出 content-outline.json。

## 整理资料

先盘点用户材料与可访问资料，记录 source ID、路径/URL、原文定位、时间、单位和许可/使用条件。需要在线研究时使用可用搜索工具，优先原始报告与官方材料，保存支持关键结论的定位；本地文档按需要加载对应解析工具，不假装已读不可访问文件。

事实表记录 id、source_id、value、unit、scope、period、metric、locator、is_demo；计算值记录 formula 及输入 ID。示意数据必须始终标示为示意。将冲突、缺失数据和未经核验的说法交还用户；不能用插画或漂亮图表充当证据。

## 制定大纲

本项目按用户要求逐页图文结合。visual_intent应说明文字如何与图片、数据图表或关系/流程图形配合；不能只写“美观配图”。按项目 `docs/页内排版与素材调用工作流.md` 为制作前的图表素材准备列出数据、来源、单位与视觉需求；无统计数据时不捏造图表。这里只准备内容和需求，风格与实际排版仍交模板/制作Skill。

围绕受众的决策设计叙事，可选结论先行、问题—证据—方案或前后对比。先给出逐页主张，再安排证据和视觉意图。每页集中一个可讲清楚的结论，控制文字量，避免连续使用同一种组织方式；这里描述信息结构，不提前决定像素坐标和字体。

每页输出 id、takeaway、evidence_refs、speaker_intent、visual_intent。takeaway 应是可理解的主张，尽量避免仅有“背景/概述”一类标签。无数据的过渡或结尾页可以 evidence_refs: []，但应说明作用。页数匹配已批准需求；核心结论不允许通过美化阶段悄悄改写。

## 输出与交接

quality-v1任务必须同时编写结构化content-plan.json，并在大纲用quality_plan指向该文件。按[内容计划合同](references/content-plan.md)写每页的问题、主张类型、证据、推理、限制、视觉证据任务、案例标签和任务专属检查问题。先串读标题检验论证推进，再检查具体情境和推论边界。不要只将一段泛泛正文拆成三栏。该附件由生产阶段哈希绑定，内容变化必须重新提交。

content-outline.json 包含 narrative、source_review_notes、sources、facts、slides。sources 使用项目来源合同的 id/kind/locator/is_demo；本地 source locator 相对项目根 ppt-workflow 解析。source_review_notes 清楚说明已读什么、冲突如何处理以及未核验项，不把资料存在当作事实真实。

用 `outline --workspace <任务目录> --input content-outline.json` 提交。需求必须先获批准。审核后交给 ppt-template；需要改主题、页数或目标时退回 ppt-intake。不要替模板 Skill 定风格，也不要生成最终 PPT 或审核自己的成品。

