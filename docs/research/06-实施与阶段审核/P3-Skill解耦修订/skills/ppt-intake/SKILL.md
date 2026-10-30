---
name: ppt-intake
description: "通过提问澄清 PPT 的受众、目标、时长、材料、品牌和编辑要求；用于开始制作前收集需求，不负责研究大纲或设计页面。"
---

# PPT 需求访谈

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责把用户的想法整理成明确需求，输出 requirements.json。入口命令为 `intake`，可单独使用；完整流程由总控路由到本 Skill。

## 工作方式

先读当前对话、已有 brief、用户提供的材料和前次回答，避免重复询问。先弄清“谁听、听后做什么、讲多久”，再补页数、语言、展示/阅读场景、品牌模板、必含内容、截止时间和可编辑要求。将明确回答、可调整的假设与仍待回答的问题分开。

一轮集中问最影响结果的 1–3 个问题，给出便于选择的选项；能继续的材料盘点不等答案。不要把所有字段变成问卷，不因可选偏好阻塞。必须项尚不明确时保留 open_questions，不能擅自把假设写成用户确认。可用异步提问工具时遵守宿主的提问规则。

用户提供 PPT/POTX 时记录路径与沿用范围，不自行承诺替换品牌。用户希望整套一致时记录色彩、字体、留白与插画一致性；希望编辑图片结构时记录“需语义重建”，不要承诺 PNG 无损拆层。

## 输出与交接

requirements.json 的字段：

- topic、audience、goal：主题、受众与希望促成的行动。
- language：zh-CN / en / zh-CN-en；delivery_mode：presented / read_alone。
- slide_count、aspect_ratio：当前本地生成范围 8–20 页、16:9；不满足时明确需要其他实现，不暗中改用户要求。
- brand、editability：品牌沿用方式、哪些元素必须原生可编辑；无品牌时可写“无强制品牌，下一阶段提出模板方案”。
- duration_minutes、constraints、material_files、assumptions：已知时记录；本地材料用真实路径。
- open_questions：[{"question":"问题","required":true,"answer":null}]；答案真实到达后才填写。

用 `intake --workspace <任务目录> --input requirements.json` 提交；它只保存和校验需求，不会替你询问用户。缺必须项为 needs_input。把具体需求稿给用户审核；已有授权可引用实际对话，不重新索要同一授权。

用户确认后，按宿主提供的准确哈希记录审批，再交给 ppt-outline。不要代做资料研究、事实核验、模板设计或最终视觉审核。完整调用及审批格式见项目 P3 解耦使用说明。

