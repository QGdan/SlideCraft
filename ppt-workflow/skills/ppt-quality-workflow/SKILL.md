---
name: ppt-quality-workflow
description: "调度本项目 PPT 六阶段 Skill：需求、资料大纲、模板、制作、美化与审核。用于启动整套流程、选择下一阶段或恢复任务；实际工作由对应阶段 Skill 执行。"
---

# PPT 工作流总控

新增compact-chart-prepare归制作Skill，image-chart由模板选择、制作执行；同页图片与图表分别准备、封存和映射，见项目docs/图片与原生图表联合表达.md。更多视觉或超容量仍调整构图/大纲，原六阶段不变。

整套制作沿用brief-compose读取原大纲与素材包。frame-catalog归模板Skill，frame-prepare归制作Skill，封面/章节/结尾与内容页一起检验节奏，见项目docs/封面章节与行动结尾.md。模板选择、真实素材准备、逐页制作和用户审核继续分工，不把固定配方当任意模板适配。

第三批迁移见项目docs/素材风格与图像叙事.md：asset-plan归模板Skill，asset-record/trend-prepare归制作Skill，审核归review。沿用详细大纲→任务素材→真实模板样页→逐页制作，生成计划不代表生成成功；现有缓存可用不代表在线服务已连通。

第二批迁移入口见项目docs/内容驱动布局与中文容量.md：layout-plan归模板Skill，page-prepare归制作Skill；大纲仍负责完整文案与叙事，审核仍看真实页面。超容量产生的拆页提案需与已批准大纲对齐，不新增阶段或自动批准。

源码迁移的首批关系能力见项目docs/内容关系与原生构图.md：大纲Skill负责信息模型，模板Skill负责配方选用，relationship-prepare归制作Skill，实际审核仍归review。保留原六阶段，不新增笼统设计Skill或工程审批。

按项目docs/视觉优先的制作约定.md执行：主要精力用于内容、选材、模板和逐页视觉打磨。保留必要的文件/数据与实际页面检查，普通排版不反复跑大规模工程测试；页面仅保留必要的数据、来源和许可标注，工程声明留在内部记录。阶段审核优先展示真实效果。

新任务默认production_mode: outline-assets-template，具体见项目docs/大纲驱动与任务素材包.md。先详细大纲及正文审核，再检索/预制并集中保存任务素材，之后确定模板和代表页，再按大纲逐页制作。素材搜集仍由模板Skill负责选材、制作Skill只执行准备子任务，保持六阶段解耦；新模式的详细brief和素材包有实际交接门禁。旧任务保持兼容。

素材链路见项目docs/在线素材检索与入页.md：asset-discover归ppt-template；asset-fetch/asset-place归ppt-compose。素材准备在批量排版前完成，后续美化与审核真实看图；在线服务失败走明确可用来源或已缓存素材，不伪造大库覆盖。

先识别任务类型。用户要求优化本项目、引擎、合同、工具链或Skill时，走工程优化：制定实现计划，按代码、合同、测试、Skill同步和结果报告推进；具体PPT仅作后续效果验证。不要要求先审核某份业务PPT的大纲或模板才能改进项目。工程检查点以实际测试和差异核查验收，不伪造业务阶段批准。

用户要求制作或修改具体PPT时，执行下述六阶段和人工审核。新任务由ppt-intake声明quality_profile: quality-v1；旧任务保持其原配置。capabilities归制作Skill，quality-check归审核Skill。新增质量合同和图表能力见项目docs/质量升级工作流.md，命令不会自动执行模型策划或审美判断。

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

“在 WPS 中找合适的模板、比较模板、下载并打样”归 ppt-template；由它实际检索与选型，不要求用户先提供下载文件。已有品牌或指定模板优先，后续制作仍交 ppt-compose，模板样页经用户审核后再批量适配。

template-catalog归模板Skill，blueprint-build归制作Skill；均不自动批准业务阶段。Canva当前连接不可用时不作为前置依赖。

图表视觉准备：chart-style-catalog归模板Skill，chart-prepare归制作Skill，按docs/原生图表视觉配方.md选型并准备绑定事实的图表＋结论。WPS副本保存后新增工作簿保留门禁，failed时不交付诊断副本；优先保留原始生产PPT并用PowerPoint实际导图。该门禁不改六阶段审核规则。

新增module-search归模板Skill、module-prepare归制作Skill；首批4类模块与2项人物插画按docs/插画与原生模块库.md调用。角色图、原生模块和真实数据图表分别准备；不把模块预览截图当作可编辑内容，也不将人物组件冒称完整场景。阶段审核沿用原协议。

素材工具：asset-search归模板Skill，asset-prepare归制作Skill；按项目docs/素材库使用.md查询5项图片及24项Tabler图标，保存选用/配色/来源/页对象记录，再进入排版。默认搜索仅旧图片，跨类型用--type all；离线可用，不依赖Canva。

常规Office/WPS任务的布局优化指每页内部文字、图表和图片的组织，不默认改变画布方向。按用户要求每页图文结合，正式制作前先整理制作相关图、表与图形。大纲→模板→制作→美化→审核沿用项目 `docs/页内排版与素材调用工作流.md`：数据和视觉需求、图表素材准备清单与真实预览、逐页布局计划、实际素材检索、选用与来源记录、真实导图复核。准备工作归原有阶段，保留审核，不新增泛化Skill。素材库按需求实际调用，缺口按实际工具补充；选型见 `docs/开源素材库研究与接入方案.md`，未接入的候选不得冒称已可调用。

`doctor` 是总控的环境诊断；plan/build/revise 归制作 Skill，qa/deliver/benchmark 归审核 Skill。保留这些底层命令作为兼容接口，不把它们当作新的通用 Skill。

每个阶段独立保存版本、附件哈希和审批记录；先提交具体产物，用户确认后才能登记审批并进入下游。已有的真实授权可以引用，不能伪造用户批准。上游修改后重新核对全部受影响阶段，不自动沿用旧审核。最终效果未验证时可以提交候选稿，不能放宽正式交付门禁。

完整阶段调用、产物字段、审批与返修说明见 [阶段交接协议](references/stage-handoffs.md)。安装入口支持选择单个 Skill 或整套安装；生产代码仍保留在绑定项目中，不进行未经当前阶段约定的全局安装。

启动前按[工具与连接](references/runtime-tools.md)检查实际能力。主线通过本地stdio客户端调用Office MCP，不依赖不存在的HTTP地址。Figma、生图及在线文档工具按当次宿主可用性检查，未连接时使用已验证主线或说明缺项，不虚构工具名、连接或模型ID。
