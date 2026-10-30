# 内容计划合同

新任务quality-v1要求大纲的quality_plan指向真实JSON，schema_version为quality-content-plan/1。完整机器合同在绑定项目schemas/content-plan.schema.json；可运行示例为examples/quality-outline.json与examples/content-plan.json。

每页写id、question、claim、claim_kind、evidence_refs、reasoning、limitations、bridge、exhibit、case、quality_checks、chart与derived。claim与已提交大纲takeaway相同，证据ID对应来源或事实。推理说明材料如何支持结论，限制写清不能推出什么。

exhibit写intent/carrier/focus/annotation/editability，描述视觉证据承担的任务，不提前伪造坐标。case区分none/source_paraphrase/teaching_example；案例转述标来源，教学情境明确标示例。quality_checks至少两条与本页内容有关的问题，不写空泛“美观吗”。

chart可为null；有数据图时记录kind/task/unit/data_refs/emphasis_refs/data_rule；构成图需明确核实互斥和完整性。derived记录id、operation、inputs、value、unit；百分比减法用百分点，不做显著性推断。

可运行quality-check预检并生成未填写审核清单；CLI不判断论证是否充分。outline阶段将该文件作为附件绑定哈希。baseline与outline_sha256为可选源文件绑定；没有旧PPT时不要为了字段而创建PPT。
