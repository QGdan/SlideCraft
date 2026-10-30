# 高质量 PPT 工作流

面向 Windows 本机 Office 的 PPT 制作与检查项目，包含需求、资料大纲、模板、制作、美化、审核六个阶段，以及调度这些阶段的总控 Skill。

当前开发入口是 `ppt-workflow/`。环境安装和验证步骤见 [团队协作指南](CONTRIBUTING.md)，功能使用见 [使用指南](ppt-workflow/使用指南.md)，当前测试限制见 [已知问题](docs/KNOWN_ISSUES.md)。

## 项目结构

| 目录 | 用途 |
|---|---|
| `ppt-workflow/ppt_workflow/` | Python 工作流和 Office 适配 |
| `ppt-workflow/engine/` | PPT 生成引擎 |
| `ppt-workflow/skills/` | 总控及六个阶段 Skill |
| `ppt-workflow/templates/`、`assets/` | 当前模板、设计配置和功能素材 |
| `ppt-workflow/tests/`、`examples/` | 测试与示例输入 |
| `ppt-workflow/scripts/`、`docs/` | 工具和功能文档 |
| `docs/research/` | 历史研究文字，不含演示稿和截图 |
| `tools/` | 源码打包工具 |

## 上传 GitHub

将源码压缩包解压后，进入包含本 README 的文件夹，在 PowerShell 中执行：

```powershell
git init
git add .
git status --short
git commit -m "Initial source import"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

先在 GitHub 创建空仓库，再把示例中的仓库地址替换为实际地址。团队成员通过分支和 Pull Request 协作。源码中没有为整个项目新增开源许可证；第三方来源见 [第三方说明](ppt-workflow/THIRD_PARTY_NOTICES.md)。

## 重新打包

在仓库根目录运行：

```powershell
python tools/package_source.py
```

输出到 `dist/ppt-workflow-github-source.zip`，附带逐文件 SHA-256 清单。压缩包不包含虚拟环境、Node 依赖、历史演示、截图、运行目录、旧实验及本机下载模板。图标、插画和当前模板预览属于功能资源，保留在包中。

历史研究文档可能引用已清理附件；这些记录不代表当前版本验证通过。本项目需要本机 Python、Node 和相应 Office 环境，源码包不是离线安装包。
