# WPS MCP 基础连接已验证

2026-10-17，用户明确允许忽略后台进程后，采用允许后台会话的只读模式，实际连接成功。此前“因后台进程而未完成”的记录已被本次结果更新。

## 实测证据

- 本地 COM：`runs/wps-readonly-20261017-001/wps-worker.json`。
- 真正 stdio MCP 调用：`runs/wps-mcp-20261017-001/mcp-client.json`，`called=probe_wps_connection`，`is_error=false`。
- 读到 `version=14.0`（COM 报告的兼容版本），`presentation_count=0`；软件安装路径产品版本为 `12.1.0.28505`，两者不混用。
- 连接既有活动对象不可用后，通过已注册的32位本地 COM 服务激活接口；不调用 Quit，不打开/保存/关闭文档。不能据此声称已附着到某个用户窗口。
- 插件目录本次搜索没有返回 WPS 插件，Document Control 无连接会话；本次成功的是**本项目 MCP 到本机 WPS 的桥接**，不是 WPS 官方云 MCP。

## 使用

在 ppt-workflow 目录执行，输出目录需新建：

```powershell
.\.mcp-venv\Scripts\python.exe scripts/office_mcp_client.py wps-health runs/新的WPS查询目录
```

服务端工具为 `probe_wps_connection(output_dir)`。现有后台进程不阻止这项只读检查；无须手工关闭 WPS。执行器仍需具备本机桌面 COM 访问权限。

直接诊断脚本也支持 `scripts/probe_wps.py runs/新目录 --allow-existing-readonly`。默认独占探测模式为历史保留模式，不适合本次已授权的后台会话检查。只读检查的 cleanupCompleted 表示引用已释放，不表示退出了 WPS。

## 能力边界

已验证：MCP握手、工具发现、工具调用、WPS应用版本与文稿数量查询。

未验证：会员身份/模板库权限、在线模板搜索下载、指定模板创建、对象编辑、保存和渲染往返。会员资格不能作为这些接口已获授权或可用的证据；实际使用模板时再核对。后续可在新测试文稿上逐项验证，不覆盖用户已打开文件。

本轮客户端三项参数/覆写保护测试通过。历史完整215项、可迁移85项回归记录保留，不把它们描述为本轮全部重跑。此前ZIP仍是当时的快照，本轮连接改动以当前项目源码为准。

## 本次后续更新

已继续验证模板编辑、保存导图、独立原生回读和会员界面下载。上文“未验证”是当时状态，当前范围与已处理的兼容问题见[WPS模板工作流](WPS-模板工作流.md)。
