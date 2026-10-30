# 团队协作指南

当前维护入口为 `ppt-workflow/`。根目录 `docs/research/` 保留历史研究文字；历史演示稿、讲稿和截图已从本地清理，不纳入仓库。

## 源码环境

既有安装脚本声明的验证环境是 Windows x64、Python 3.12；Office 自动化还需要本机 PowerPoint 或对应的 WPS 环境。以下安装方式需要联网，本次整理未重新验证依赖下载和全新安装。

在仓库根目录打开 PowerShell：

```powershell
cd ppt-workflow
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm ci
```

需要本地 Office MCP 服务时，再创建独立环境：

```powershell
py -3.12 -m venv .mcp-venv
.\.mcp-venv\Scripts\python.exe -m pip install -r office-mcp/requirements.lock.txt
```

`scripts/bootstrap.py` 面向包含 `vendor/` 的离线整理包，不能直接用于普通 Git 源码目录。保留依赖锁文件，不提交虚拟环境、`node_modules/` 或 `runs/`。

## 验证修改

在 `ppt-workflow/` 中执行：

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts/smoke.py --node (Get-Command node).Source
```

这运行可迁移测试子集，不代表 PPT 视觉验收。整理前该检查有 3 个失败；最新结果与限制见 [已知问题](docs/KNOWN_ISSUES.md)。全量测试中的部分用例依赖已清理的历史夹具，应在重新准备集成材料后运行。

## 提交协作

从主分支新建功能分支，完成修改和相关检查后提交 Pull Request，说明修改目的、涉及目录及验证结果。不要提交本机绝对路径、账号凭据、私人任务资料或未获共享授权的外部模板。

当前素材和模板配置属于功能资源；历史演示和截图不再作为测试证据。研究归档中的旧路径和验证结论仅供追溯。运行测试生成的临时 PPT、截图与报告应留在被忽略的 `runs/` 下。
