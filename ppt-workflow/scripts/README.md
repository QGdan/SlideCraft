# 脚本入口

日常操作首先使用 `python -m ppt_workflow`，并加载所属阶段Skill。

| 脚本 | 用途 |
|---|---|
| create_demo.py | 生成本机路径绑定的示意输入；不是业务审批 |
| office_mcp_client.py | 主线调用的stdio客户端；health/catalog/unified-template/instantiate/enhance/inspect-template/wps-health/wps-template |
| verify_connections.py | 新目录中实测6个MCP操作、6阶段路由和10页构建渲染 |
| smoke.py | 当前89项可迁移检查 |
| bootstrap.py | 只在含vendor的全新解压包内离线安装 |
| install_skill.py | 预览或新安装Skill，不覆盖已有目录 |
| sync_installed_skills.py | 维护时备份并更新已绑定本项目的七个副本 |
| package_runtime.py | 从当前源码与已核对的历史依赖包创建新整理包 |

plan_cleanup.py与apply_cleanup.ps1仅为2026-10-17本次清理的已列目录维护脚本，不用于删除任意任务或移除Office锁。所有删除先生成清单、检查绝对目标边界及reparse point，并保留记录。

其余build_p2、run_p3、package_p5、prepare_p5等脚本是阶段实验/打包记录，依赖历史run，不作为日常入口。清理保留了相应成品及审核ZIP；重复安装环境已删除，若要复现实验需按相应版本重新安装，不能直接resume旧绑定任务。

probe_wps.py默认独占探测；加--allow-existing-readonly可在有后台进程时只读查询。wps-health通过MCP调用该只读模式，不退出WPS，不等同模板编辑和渲染适配。
