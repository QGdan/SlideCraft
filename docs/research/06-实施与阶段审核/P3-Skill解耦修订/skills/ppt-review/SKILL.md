---
name: ppt-review
description: "独立检查 PPT 内容、原生编辑性、渲染与跨页视觉效果，生成通过、返修或未验证结论；适用于审核与交付门禁，不负责代为美化或改事实。"
---

# PPT 效果审核

项目位置见相邻 runtime.json；在该项目虚拟环境运行 `python -m ppt_workflow`。本 Skill 可单独执行本专业任务；使用持久化阶段命令时仍需有效的上游交接件。

负责审核结果与问题定位，入口命令为 `review`；底层 qa / deliver / benchmark 归本 Skill 所有。先读已批准的需求、大纲、模板和美化后成品，而不是只读制作者的总结。

## 审核

运行静态 QA、事实/公式和原生对象检查，绑定本次 PPT、spec、渲染清单与逐页图片哈希。查看接触表检查跨页节奏，再逐页查看全尺寸图，重点检查标题换行、越界、重叠、对齐、数据标签、中文字体、图像裁切和整套一致性。

内容审核核对来源、数值、单位、时间、统计口径和示意标记。将必须修的问题定位到 slide/element，并给出可执行的返修建议。制作未按大纲或模板执行，退回 ppt-compose；版式与措辞打磨退回 ppt-polish；事实或模板本身有问题，退回相应上游 Skill 后重审下游。不要在审核记录里悄悄替作者修改文件。

使用宿主图像审阅时保存实际逐页观察与跨页、内容判断；使用视觉 API 前预留额度，初次与失败共三次。视觉检查不能替代没有执行的 OOXML schema 校验、交互编辑往返或其他未覆盖检查，零 error 也不等于全面通过。

## 输出与正式交付

review-report.json 包含 qa_report、automated_qa、render_manifest、visual_review、assessment、decision。文件指向本次真实检查记录，visual_review 的 binding 必须对应 deck/spec、原自动 QA 和完整渲染图。decision 与真实检查一致：failed / unverified / needs_review / passed，不用平均分覆盖严重缺陷。

用 `review --workspace <任务目录> --input review-report.json` 提交。用户批准审核报告只表示接受该阶段的判断；若判断仍为 unverified，并不授权正式发布。

底层 deliver 仅允许 ready + QA passed、零未解决 warning/unknown 且视觉记录有效时放行。当前示例仍有部分自动检查 unknown，保留候选稿状态，不删除 unknown 或伪造 passed。benchmark 只报告已测本地指标，不冒充外部引擎对照。底层命令与视觉记录格式见 references/engine-cli.md。

