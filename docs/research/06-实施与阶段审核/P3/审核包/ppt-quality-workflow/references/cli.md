# 命令与审核记录

在绑定的 `ppt-workflow` 目录运行 `.venv/Scripts/python.exe -m ppt_workflow`，或使用本 Skill 的 `scripts/run.py`。输出 JSON；退出码 0 表示命令执行成功，1 表示失败或被门禁拒绝，2 表示仍待审核/未验证。`plan` 成功不表示成品通过。

## 确定输入

配置例见项目 `examples/workflow-unified.json`。字段：`brief`、`spec`、`template`、`design_system`、`node`、`renderer`、`timeout_seconds`、`design_approval`，可选额外 `source_files`。

配置中相对路径按配置文件目录解析；spec 的本地 source locator 按项目目录解析；资产按登记路径解析。所有输入限定项目内部。当前版使用已确认的 unified-v3 设计系统与原生 POTX。审批记录包含 spec/template/design 的 SHA256、reviewer 和实际审批依据，不能伪造用户批准。

```powershell
.\.venv\Scripts\python.exe -m ppt_workflow doctor
.\.venv\Scripts\python.exe -m ppt_workflow plan --config examples/workflow-unified.json --out runs/my-job
.\.venv\Scripts\python.exe -m ppt_workflow build --run runs/my-job --with-qa
.\.venv\Scripts\python.exe -m ppt_workflow build --run runs/my-job --resume
```

最后一个命令只恢复未变更的构建，不重启 Office。模板必须先存在并已审核；CLI 不会随内容悄悄重新选择模板。

## 视觉记录

首次 QA 生成 `rev-000/qa-000/review-request.json`。复制到独立文件；保持 binding 原样，写明 `status: passed`、reviewer、实际 method，以及每页真实观察，补充 consistency_notes 和 content_notes。不要只根据接触表填写所有细节通过。

```powershell
.\.venv\Scripts\python.exe -m ppt_workflow qa --run runs/my-job --review runs/my-job/host-review.json
```

第二次 QA 保留被审阅的原自动报告，避免时间戳变化使 binding 无故失效。附加视觉记录不会把其他未覆盖项改成通过。

使用外部视觉 API 时，先调用 `qa --run runs/my-job --reserve-visual-call`，每张 ticket 只调用一次 API，失败不退额度。成功记录中的 method 为 `visual-api`，`visual_ticket` 对应本次 ticket ID。CLI 不代为发送图片或调用付费服务。没有 API 时直接使用宿主图像审阅，不需要 ticket。

## 有限修复

`revise --run runs/my-job --patch repair.json` 只接受以下格式：

```json
{"changes":[{"element_id":"s02-e07","issue_id":"typography-1","rect":{"x":0.8,"y":4.72,"w":6.2,"h":1.27}}]}
```

issue_id 必须来自该版本实际 QA，且输出对象映射必须对应 element_id；上例仅示意，不能套用不存在的问题。仅能在原位置扩大正文框，每维最多 0.5in，并检查与其他对象相交、模板区域及事实表。修复后重新 build/qa，旧审核不继承；最多两轮。

环境重试：给失败的 `build` 或 `qa` 加 `--retry-environment`，全任务共一次。隔离锁存在时先查清 worker 状态，不自动删除锁、不反复重试。

## 交付与测量

```powershell
.\.venv\Scripts\python.exe -m ppt_workflow deliver --run runs/my-job --out runs/my-delivery
.\.venv\Scripts\python.exe -m ppt_workflow benchmark --runs runs/my-job
```

正式交付要求状态 ready、完整 QA passed、逐页视觉记录有效，且没有未解决 warning/unknown。目录含 PPT、spec、brief、来源与模板副本、对象映射、检查记录、PNG、哈希清单和 ZIP；成品目录必须独立且不存在。

benchmark 只汇总已记录的本地构建/渲染时长与 QA 状态，未知费用、人工修改时长为 null。它不等于 P4 的跨开源引擎比较。

当前样例仍有全量 OOXML schema 等 unknown，因此可以提交候选稿和审核包，不能宣称已通过正式 deliver。此限制应在阶段审核中明确列出。
