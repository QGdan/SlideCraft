---
name: ppt-polish
description: "在既有 PPT 和已批准模板内优化版式、图形、图表表达与正文措辞；适用于成品美化，不重新研究事实、不替代最终效果审核。"
---

# PPT 美化与润色

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责“把已做好的 PPT 打磨好”，入口命令为 `polish`。读取获批的 composition.json、模板和原生成品；先看全套接触表，再看重点页与全尺寸图。

## 打磨方法

先查跨页一致性：背景、字体层级、页眉页脚、页码、间距和插画材质是否一致。再优化信息层级、对齐、空白、数字强调、图表标签与配色、表格密度和流程阅读顺序。每处修改关联页/element ID 与具体原因，不通过加装饰掩盖信息不清楚。

可精简冗余正文和改善措辞，但不改事实、口径、计算结果、图表/表格数据、流程语义和已批准的逐页主张。核心结构或主张需要改变时退回 ppt-outline / ppt-compose，品牌、模板、字体系统和背景变更退回 ppt-template。

需要新插画时使用可用 imagegen Skill，沿用模板的色彩、材质、光源和留白；正确登记新素材。需要编辑矢量图层或 Figma 元素时加载对应插件 Skill，在实际图层操作并截图检查。图像生成器未公开模型 ID 时不要声称指定了 Image 2；PNG 不能自动无损拆成原生图层。

## 输出与交接

polish-report.json 包含 deck、deck_spec（改后实际文件）、visual_notes、copy_notes、changes。changes 为 [{"element_id":"…","change":"具体修改","reason":"对应问题"}]；确实无需修改时可为空，但说明查看过哪些页面以及为什么保留。

保持事实和主张可追溯，输出原生 PPT 与 spec 相符。用 `polish --workspace <任务目录> --input polish-report.json` 提交，审核后交给 ppt-review。自查用于定位和修复，不等于最后的审核结论；未看到截图不要写“已美化完成”。

