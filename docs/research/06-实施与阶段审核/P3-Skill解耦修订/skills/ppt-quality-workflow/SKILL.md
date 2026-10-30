---
name: ppt-quality-workflow
description: "调度本项目 PPT 六阶段 Skill：需求、资料大纲、模板、制作、美化与审核。用于启动整套流程、选择下一阶段或恢复任务；实际工作由对应阶段 Skill 执行。"
---

# PPT 工作流总控

只负责识别当前阶段、定位阶段产物、调用对应 Skill、遵守审核交接和失败预算，不承担六种专业工作。

先运行项目虚拟环境中的 `python -m ppt_workflow skills` 获取当前命令—Skill 注册表。项目位置见相邻 runtime.json。根据已有材料从适当阶段进入；在本工作流的持久化任务中，先检查已批准的上游交接件，不能直接跳过。

| 阶段命令 | 调用 Skill | 输出 |
|---|---|---|
| intake | ppt-intake | 需求与待回答问题 |
| outline | ppt-outline | 来源、事实表、叙事及逐页大纲 |
| template | ppt-template | 模板、设计系统与真实样页 |
| compose | ppt-compose | 原生成品、spec 与修改记录 |
| polish | ppt-polish | 美化后成品与润色记录 |
| review | ppt-review | 检查、逐页视觉记录及审核结论 |

读取注册表返回的绝对 SKILL.md 路径，告知用户当前正在使用哪个阶段 Skill，再按该 Skill 完成工作。终端命令不能自动加载语言模型 Skill：无 --input 时只返回路由与交接状态；执行过命令不等于完成访谈、研究、设计或视觉审核。

`doctor` 是总控的环境诊断；plan/build/revise 归制作 Skill，qa/deliver/benchmark 归审核 Skill。保留这些底层命令作为兼容接口，不把它们当作新的通用 Skill。

每个阶段独立保存版本、附件哈希和审批记录；先提交具体产物，用户确认后才能登记审批并进入下游。已有的真实授权可以引用，不能伪造用户批准。上游修改后重新核对全部受影响阶段，不自动沿用旧审核。最终效果未验证时可以提交候选稿，不能放宽正式交付门禁。

完整阶段调用、产物字段、审批与返修说明见 [阶段交接协议](references/stage-handoffs.md)。安装入口支持选择单个 Skill 或整套安装；生产代码仍保留在绑定项目中，不进行未经当前阶段约定的全局安装。
