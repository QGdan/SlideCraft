# 原生场景模板蓝图

在绑定项目运行 `python -m ppt_workflow template-catalog`。目前campus-editorial-v1提供ivory/ink两个色彩变体、五个专用布局（含两种行动构图）：封面、证据、比较、场景行动。只有这一套原创模板，不是任意PPT或网页模板的自动转换器。

模板配置在templates/campus-editorial-v1/blueprint.json，包含语义色、字号、图片位、文字容量和图表容量。先看完整蓝图和素材，再制作代表样页；不能只挑一个背景。模板选择仍服从用户品牌与已有批准件。

用examples/campus-blueprint.json运行制作Skill的blueprint-build，可生成含实际命名原生布局的PPTX、design-system及spec。这个PPTX可以作为模板阶段真实样件；JSON蓝图不能伪称POTX母版。模板样件的不同构图应一起审阅，并核对布局名称。

封面和行动页图片属于可替换位图，正文、图表与过程是原生对象。AI场景仅作示意，不能证明真实活动已发生。图片提示词、来源、SHA256和许可说明见assets/campus-editorial-v1/。

人审后才登记template批准、适配真实大纲。命令能构建不代表视觉通过，不自动批准下游。旧unified-v3计划构建链继续独立保留。
