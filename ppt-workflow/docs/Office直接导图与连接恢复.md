# Office直接导图与连接恢复

2026-10-19本机实测：Python启动PowerShell的PowerPoint导图失败，直接PowerShell启动同一worker成功；更换PowerShell版本、TEMP或取消CREATE_NO_WINDOW没有消除Python启动链的失败。原因未完全定位，不能把它笼统归为PPT损坏、软件损坏或PowerShell版本问题。

当前新增直接PowerShell入口作为可复用备用通路。PowerPoint16.0/build20430导图及WPS MCP保存/独立回读已经通过，并实际查看了技术验证页；这些是指定页面的证据，不是任意模板均兼容的保证。

## PowerPoint备用导图

在终端直接执行以下PowerShell命令，cwd为ppt-workflow；使用PowerShell7，不要再从Python subprocess启动这个入口。输出目录必须是runs下未存在的目录：

```powershell
& ./scripts/render_direct.ps1 -Pptx ./runs/任务/candidate.pptx -Out ./runs/任务-direct-render -Timeout 60
```

流程：取得原有Office互斥锁→隐藏启动独立worker→限制执行时间→核对退出码和清理证据→检查输入哈希、页数、1600×900实际PNG→保存render-manifest.json。调用已有render/windows.ps1，不接管已存在的PowerPoint会话。默认60秒，允许1–120秒；超时仅停止本次helper，Office清理不确定时保留隔离锁，不全局结束应用或自动删除锁。

未生成manifest或manifest不是passed均不得视为导图通过。manifest通过只表示导图与文件核对完成；审核Skill仍须逐页看图、检查文字和素材。入口不会自动更改六阶段的批准状态。

如果用户PowerPoint仍打开，不关闭用户会话来强行导图；可使用已连接WPS的副本路线，或报告本次未验证。直接入口不是Python命令已经修复的声明，常规CLI仍保留供其他环境使用。

## WPS激活失败后的有限恢复

WPS MCP返回activate阶段“服务器运行失败”时，本机一次直接PowerShell只读激活后，原MCP实际恢复了保存、导图和独立回读。执行：

```powershell
& ./scripts/activate_wps.ps1 -Out ./runs/任务-wps-activation
# 确认wps-direct-connection.json为connected后，用新目录重试原请求一次
.\.mcp-venv\Scripts\python.exe scripts/office_mcp_client.py wps-template runs/任务-wps-retry runs/任务/request.json
```

activate_wps只读取版本和文稿数量，不打开或修改文件，不调用Quit，不改注册表，也不切换系统位数。connected只表示只读连接成功，保存、导图与回读仍以MCP三个真实结果为准。恢复失败或重试后仍失败则保留记录并停止该恢复路径，不反复重启共享WPS。

不将这种观察宣称为通用根因修复。若后续机器出现不同错误，应查看phase、worker错误及清理记录，再决定处理。

## 本轮视觉复核

技术页003的WPS导图暴露“关系图”孤字换行。004显式规划四列正文的两行断句；PowerPoint直接入口与WPS MCP均实际导图成功。已查看两端完整页面，图标透明区域、颜色、箭头、文字与标签对应正常。技术页证明素材可以被检索、登记、放入原生内容旁并导图，不代表已完成全套业务PPT的设计质量审核。
