# 六阶段调用与交接协议

注册表单一来源为项目 skill-routing.json。skills 命令返回阶段/底层命令所属的 Skill 和绝对文件路径。宿主必须加载该文件后执行专业工作；CLI 仅验证和记录，不会发起模型调用。

```powershell
python -m ppt_workflow skills
python -m ppt_workflow intake --workspace runs/my-stage-job
python -m ppt_workflow intake --workspace runs/my-stage-job --input requirements.json
```

不带 --input 时返回当前状态、应调用的 Skill 和期望产物。提交后保存独立版本、输入附件哈希、当前 Skill 哈希与上游批准件哈希。缺必需信息为 needs_input；完整草稿为 needs_review，不能仅因格式合法就批准。

得到真实用户批准后，使用刚才返回的完整 artifact_sha256 登记：

```powershell
python -m ppt_workflow intake --workspace runs/my-stage-job --approve <完整哈希> --reviewer user --evidence "实际批准依据"
python -m ppt_workflow outline --workspace runs/my-stage-job
```

不能拿文档中这段示例充当审批依据。审批记录仅表示阶段交接，不是最终发布批准。没有有效上游审批时阻止下一阶段。

依次使用 outline、template、compose、polish、review，同样支持 --input 和准确哈希审批。六个输入 JSON 字段由各自 SKILL.md 定义。路径按提交 JSON 所在目录解析；sources 的本地 locator 按项目 ppt-workflow 根解析。

修改上游时重新提交该阶段，保留旧版本。所有下游会因上游哈希不匹配而失效；修改附件或 Skill 规则也会使对应交接失效，必须重新核对和批准，不只是改一个状态字符串。若退回需求、主张或模板，重新执行受影响下游；底层引擎同时会检查自己的输入哈希。

美化允许优化非事实正文和新增装饰图形，但不能改事实、数据、来源口径、流程语义或已批准的标题主张。模板背景、品牌字体与主色变化应退回 template。审核会检查其目标就是 polish 的输出，并保留原自动 QA 的未覆盖项。

单个 Skill 可以直接被用户调用执行局部工作；如果要将结果写入这套持久化交接链，仍应登记所需上游资料与真实批准。不要为了绕过依赖伪造历史。旧七命令继续作为底层兼容接口，直接执行不表示六阶段交接已获批准。

安装所有阶段及总控：scripts/install_skill.py --dest <父目录> --apply。仅安装一个：追加 --skill ppt-polish。默认只预览，不覆盖任何已存在目标；这些是项目绑定型 Skill，runtime.json 指向生产代码，非独立离线运行包。个人全局安装仍按项目阶段安排。
