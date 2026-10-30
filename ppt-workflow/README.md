# PPT 六阶段工作流

当前实现包含总控 Skill 及需求、资料大纲、模板、制作、美化、审核六个阶段。业务任务逐阶段审核；工程测试不代替内容和视觉审核。

- 安装与协作：[团队指南](../CONTRIBUTING.md)
- 调用与命令：[使用指南](使用指南.md)
- 测试限制：[已知问题](../docs/KNOWN_ISSUES.md)
- 当前能力：[工具与连接](docs/工具与连接.md)
- 交接协议：[阶段交接](skills/ppt-quality-workflow/references/stage-handoffs.md)
- 来源记录：[第三方说明](THIRD_PARTY_NOTICES.md)

## 本机命令

先按团队指南安装环境，再在本目录执行：

```powershell
.\.venv\Scripts\python.exe -m ppt_workflow doctor
.\.venv\Scripts\python.exe -m ppt_workflow skills
.\.venv\Scripts\python.exe -m ppt_workflow intake --workspace runs/my-job
```

Skill 安装入口为 `scripts/install_skill.py --dest <父目录>`，默认预览，添加 `--apply` 才复制，已有目标不覆盖。本机 CLI 不会替用户执行访谈、研究或内容审核。

源码目录不含离线 `vendor/`，不能直接使用面向离线包的 `bootstrap.py`。下载的外部会员模板不随源码分发；`templates/imported/README.md` 说明如何提供本地模板。

## 测试与历史材料

执行 `python scripts/smoke.py --node <实际node路径>` 运行可迁移子集。当前已知失败见上方已知问题；不能将命令完成等同于整套 PPT 质量通过。

历史演示稿、讲稿、截图已清理。全量集成用例可能依赖这些旧夹具；历史工具也可能需要旧实验或运行目录。当前模板的图标、插画、配置和模板预览作为功能资源保留，editorial-wine 旧参考演示和预览已移除，仅保留设计配置及来源说明。

历史研究文字集中在 `../docs/research/`，旧文档中的历史链接、认证状态和验收记录仅供追溯。
