---
name: ppt-template
description: "根据需求和大纲选择或创建完整 PPT 模板、视觉系统与代表样页；适用于确定整套风格，不负责撰写事实内容或逐页成品制作。"
---

# PPT 模板选择与创建

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责“整套看起来是什么样”。入口命令为 `template`，读取已批准的需求与大纲，输出真实模板、设计规范、预览和 template-selection.json。

## 选择或创建

有用户品牌模板时先检查母版、布局、字体、图片位、图表和页码，说明可沿用与不支持的部分。没有模板时，根据受众、主题和场景提出合适风格；展示代表样页让用户选方向，不反复展示没有差异的方案。

先固定背景、角色色、字体与字号层级、网格、边距、页眉页脚、图表语法和插画风格，再定义封面、主张、指标、对比、证据、流程、时间线、表格、章节与结尾等所需版式。布局可以有变化，视觉语言应一致。避免只换背景色却称为完整模板。

用真实 POTX/PPTX 母版或 Figma 主题/可复用布局展示模板。新建 Figma 文件与执行插件操作时加载当时可用的对应 Figma Skill；不假设插件连接长期有效。需要位图时使用可用 imagegen Skill，统一背景、材质、光线、比例和留白。图表和真实数字保留为原生内容。

## 输出与能力边界

template-selection.json 包含 template_path、design_system、preview_paths、layout_keys、selection_rationale、asset_guidance、editability_policy。前三项指向真实文件；预览不能只是尚未生成的路径。design_system 至少包含 font、colors、layouts；colors 明确 background/ink 等角色，layouts 使用 key。

当前本地 compose 引擎只验证了 unified-v3；模板 Skill 可以设计其他模板，但必须在交接中明确引擎兼容性，由制作阶段验证或报告阻塞，不能用统一模板冒充用户模板。

通过 `template --workspace <任务目录> --input template-selection.json` 提交，用户确认整套规范后才交给 ppt-compose。模板资产或设计规范变化会使下游失效。不要在本阶段填满正式内容，不修改事实与大纲。

