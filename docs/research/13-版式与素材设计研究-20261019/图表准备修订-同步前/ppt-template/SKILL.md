---
name: ppt-template
description: "根据需求和大纲，在 WPS 中搜索筛选并复用 PPT 模板，或按品牌创建视觉系统与代表样页；用于模板选型和整套风格确定，不负责事实撰写或成品制作。"
---

# PPT 模板选择与创建

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责“整套看起来是什么样”。入口命令为 `template`，读取已批准的需求与大纲，输出真实模板、设计规范、预览和 template-selection.json。

先按[版式与素材选择](references/visual-composition.md)明确阅读顺序、构图候选与图片角色；asset-search提供本地素材筛选，不代替设计判断。

## 选择或创建

有用户品牌模板时先检查母版、布局、字体、图片位、图表和页码，说明可沿用与不支持的部分。没有模板时，根据受众、主题和场景提出合适风格；展示代表样页让用户选方向，不反复展示没有差异的方案。

没有指定品牌模板且 WPS 可用时，主动进入 WPS 模板库，按需求搜索、比较候选并选择适合的模板，不默认要求用户先手工下载。用户要求“去 WPS 找合适模板”时，本 Skill 负责执行检索与选型。读取 [WPS 模板搜索与筛选](references/wps-template-selection.md)，按真实界面完成浏览、详情核对、下载、原生对象盘点和代表页打样；展示实际效果与选择理由后交用户审核。用户指定模板、品牌和风格优先，不因会员库方便而替换。

优先复用用户选择并有权使用的 Office/WPS 原生模板与模块。将 POTX/PPTX 放入绑定项目 `templates/imported/`，通过 `.mcp-venv/Scripts/python.exe scripts/office_mcp_client.py inspect-template runs/新检查目录 templates/imported/模板.pptx` 生成母版、布局、主题和对象清单；WPS 的 DPS 先另存 PPTX。该工具仅检查文件，不打开软件、不抓取在线商城，也不表示任意模板已兼容 compose 引擎。POTX 可用 instantiate 创建独立副本；PPTX 内容页的二次开发需建立逐页对象映射后验证。

先制作封面、数据/图表页、流程/复杂内容页三张代表样页，必要时使用统一提示词生成设计参考图，再展示整套接触表供用户审核。参考图决定构图与视觉规范；真实文字、数据、表格与流程仍应落为原生对象。完成“模板选择→资源盘点→三页打样→用户审核→批量适配”，再交制作阶段；记录模板来源及使用范围。

先固定背景、角色色、字体与字号层级、网格、边距、页眉页脚、图表语法和插画风格，再定义封面、主张、指标、对比、证据、流程、时间线、表格、章节与结尾等所需版式。布局可以有变化，视觉语言应一致。避免只换背景色却称为完整模板。

用真实 POTX/PPTX 母版或 Figma 主题/可复用布局展示模板。新建 Figma 文件与执行插件操作时加载当时可用的对应 Figma Skill；不假设插件连接长期有效。需要位图时使用可用 imagegen Skill，统一背景、材质、光线、比例和留白。图表和真实数字保留为原生内容。

使用本地原创场景模板时，先读[场景蓝图](references/scene-blueprints.md)，运行template-catalog检查实际布局与变体。蓝图构建的真实PPTX可作代表样件，仍需模板审核。

## 输出与能力边界

quality-v1任务需要为设计系统提供semantic_layouts，按[语义版式与容量](references/semantic-layouts.md)声明各版式可承载的表达任务、文字和图表容量。用大纲的视觉任务选布局；统一色板和层级，允许数据、关系、案例和行动页使用不同构图。背景一致不能代替设计系统，版式变化也不以卡片数量衡量。

WPS 的检索、下载、许可登记及本地 MCP 打样步骤见上述参考。桌面 COM 不是商城搜索 API；会员身份不代表所有模板均可商用或再分发。用户下载的模板不进入通用安装包。模板预览、下载成功、原生编辑检查和用户批准分别记录，不混为已通过。

template-selection.json 包含 template_path、design_system、preview_paths、layout_keys、selection_rationale、asset_guidance、editability_policy。前三项指向真实文件；预览不能只是尚未生成的路径。design_system 至少包含 font、colors、layouts；colors 明确 background/ink 等角色，layouts 使用 key。

旧统一计划构建链仍限unified-v3；新增独立场景蓝图编译支持本项目五种命名布局。其他模板须实际适配，不能用统一模板或蓝图冒充用户指定模板。

通过 `template --workspace <任务目录> --input template-selection.json` 提交，用户确认整套规范后才交给 ppt-compose。模板资产或设计规范变化会使下游失效。不要在本阶段填满正式内容，不修改事实与大纲。

