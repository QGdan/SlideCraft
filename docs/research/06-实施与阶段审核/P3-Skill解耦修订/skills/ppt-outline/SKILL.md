---
name: ppt-outline
description: "整理、核对 PPT 资料和事实来源，设计叙事与逐页大纲；适用于已有需求后研究内容，不负责模板绘制或成品视觉审核。"
---

# PPT 资料与大纲

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责“讲什么、凭什么、怎么讲”。入口命令为 `outline`；读取已批准的 requirements.json，输出 content-outline.json。

## 整理资料

先盘点用户材料与可访问资料，记录 source ID、路径/URL、原文定位、时间、单位和许可/使用条件。需要在线研究时使用可用搜索工具，优先原始报告与官方材料，保存支持关键结论的定位；本地文档按需要加载对应解析工具，不假装已读不可访问文件。

事实表记录 id、source_id、value、unit、scope、period、metric、locator、is_demo；计算值记录 formula 及输入 ID。示意数据必须始终标示为示意。将冲突、缺失数据和未经核验的说法交还用户；不能用插画或漂亮图表充当证据。

## 制定大纲

围绕受众的决策设计叙事，可选结论先行、问题—证据—方案或前后对比。先给出逐页主张，再安排证据和视觉意图。每页集中一个可讲清楚的结论，控制文字量，避免连续使用同一种组织方式；这里描述信息结构，不提前决定像素坐标和字体。

每页输出 id、takeaway、evidence_refs、speaker_intent、visual_intent。takeaway 应是可理解的主张，尽量避免仅有“背景/概述”一类标签。无数据的过渡或结尾页可以 evidence_refs: []，但应说明作用。页数匹配已批准需求；核心结论不允许通过美化阶段悄悄改写。

## 输出与交接

content-outline.json 包含 narrative、source_review_notes、sources、facts、slides。sources 使用项目来源合同的 id/kind/locator/is_demo；本地 source locator 相对项目根 ppt-workflow 解析。source_review_notes 清楚说明已读什么、冲突如何处理以及未核验项，不把资料存在当作事实真实。

用 `outline --workspace <任务目录> --input content-outline.json` 提交。需求必须先获批准。审核后交给 ppt-template；需要改主题、页数或目标时退回 ppt-intake。不要替模板 Skill 定风格，也不要生成最终 PPT 或审核自己的成品。

