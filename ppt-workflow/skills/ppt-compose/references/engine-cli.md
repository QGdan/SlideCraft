# 制作命令

在 runtime.json 指定的项目使用虚拟环境运行：

```powershell
python scripts/create_demo.py --node <本机node.exe绝对路径> --out examples/my-demo
python -m ppt_workflow plan --config examples/my-demo/workflow.json --out runs/my-job
python -m ppt_workflow build --run runs/my-job
python -m ppt_workflow build --run runs/my-job --resume
```

config 的 brief/spec/template/design_system 相对配置文件解析；design_approval 需绑定 spec/template/design 的 SHA256、实际 reviewer 与 evidence。当前本地 Office 桥接输入限定 ppt-workflow 内，外部资料应先按授权整理进项目。stage 命令的资料文件可在整个项目文件夹内，二者范围不同。

以上create_demo仅为明确示意的安装自检，会重新登记本机素材路径；正式任务必须采用已批准的大纲和模板，不沿用demo审批。运行命令时使用绑定项目的 .venv/Scripts/python.exe，而非不明系统Python。

plan 负责校验、冻结与输出构建 outline.json，不执行资料研究。build 通过 MCP 调用 Office；--resume 只接受哈希未变的任务。新增阶段命令 compose 负责提交 composition.json；终端本身不调用语言模型 Skill。持久化阶段中的制作输入必须来自获批的资料大纲和模板。

revise 的格式：

```json
{"changes":[{"element_id":"s02-e07","issue_id":"typography-1","rect":{"x":0.8,"y":4.72,"w":6.2,"h":1.27}}]}
```

实际 issue_id 必须存在且指向该对象；上例只是格式，不可伪造缺陷。执行 revise --run <任务> --patch <文件> 后新建 revision，重新 build，再交审核 Skill。正文框只能原位置扩大，每维最多 0.5in，不得碰撞、改字体、改事实或品牌，最多两轮。

build --retry-environment 仅重试环境故障，全任务共一次。已有 Office 会话或隔离锁由 worker 保护，不全局结束进程。build --with-qa 是保留的兼容便捷入口；运行其中 qa 不等于调用过 ppt-review 或完成了逐页审核。
