# 审核与交付命令

```powershell
python -m ppt_workflow qa --run runs/my-job
python -m ppt_workflow qa --run runs/my-job --review runs/my-job/host-review.json
python -m ppt_workflow deliver --run runs/my-job --out runs/my-release
python -m ppt_workflow benchmark --runs runs/my-job
```

首次 qa 生成不可变 automated-qa.json、检查细节、对象映射、渲染与 review-request.json。复制 request 到独立文件，保持 binding 原样，写实际 reviewer、method、逐页 status/notes、consistency_notes 与 content_notes，真实看过全尺寸图后再填写 passed。附加视觉记录不会清除其他 unknown。

host-image-inspection 不需要 API ticket；visual-api 在调用之前先执行 qa --reserve-visual-call，记录成功 ticket 的 ID 到 visual_ticket，每张 ticket 只调用一次，失败也消耗额度，含初次共三次。CLI 只管理额度，不自动调用外部服务。

render 失败可显式 qa --retry-environment，全任务环境重试共一次。输入、资产、模板、引擎或图像变化都会使原审核失效。输出必须使用新目录，不能拿旧 PNG 冒充新渲染。

阶段 review 命令提交 review-report.json，引用最终 qa.json、原 automated-qa.json、render-manifest.json 与 visual-review.json，验证当前美化成品与审核哈希一致。阶段报告获批不等于 release 通过。deliver 仍要求 ready、QA passed、没有未解决 warning/unknown，且所有复制文件复核哈希。

benchmark 仅汇总实际记录的本地测量，未记录费用和人工修改时间为 null。退出码：0 为命令完成，1 为失败或门禁拒绝，2 为 needs_review/unverified。必须将当前覆盖限制写进最终判断。
