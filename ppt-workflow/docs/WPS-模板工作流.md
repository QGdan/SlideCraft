# WPS 会员模板到可编辑 PPT 的工作流

2026-10-19新增实测限制：本机WPS转存原生图表验证稿时虽可导图，却丢失嵌入工作簿。wps-template现在增加chart-preservation.json，源有工作簿而副本丢失时返回failed，不能只凭保存/导图/文字回读认定图表数据完整。处理与范围见[原生图表视觉配方](原生图表视觉配方.md)；历史记录仅代表当时检查范围。

2026-10-17实测：会员库在桌面界面可用，模板下载、原生对象盘点、MCP 按对象改稿、保存、导图和独立进程回读均已执行。这里没有假设存在会员模板商城的公开 MCP/API。

## 已验证的路线

1. ppt-template：在已登录的 WPS 客户端选择模板，检查详情页使用范围，点击立即使用，另存为项目 `templates/imported/` 下 PPTX。本次下载《绿色简约风工作总结汇报》，实际16:9、16页、1母版、6布局、7个原生图表，文字和图形均有可编辑对象。
2. 运行 `inspect-template`，生成原生布局/主题/形状 ID 清单。模板可包含位图装饰，不能把位图背景当作全部原生矢量；文字和数据是否可编辑逐项检查。
3. 根据获批大纲选择封面、图形页和图表页打样。请求 JSON 指定 source pages；文字修改使用精确的源页号、shape_id、expected 和 text，不匹配则停止。
4. 运行 `wps-template`。先制作文件快照，避免原模板仍在 WPS 中打开时触发占用提示；优先连接活动 WPS，只操作自己的副本，不退出应用。
5. 保存并输出1600×900 PNG，再用独立进程只读重开核对修改。保存、导图、回读任一步失败均不作为成功交付。
6. ppt-polish/ppt-review 检查逐页图像、跨页一致性和图表数据。三页设计提交用户审核，通过后再批量适配业务内容；不会自动修改既有批准模板或人工审核结论。

在 ppt-workflow 目录执行：

```powershell
.\.mcp-venv\Scripts\python.exe scripts/office_mcp_client.py inspect-template runs/new-inspection templates/imported/模板.pptx
.\.mcp-venv\Scripts\python.exe scripts/office_mcp_client.py wps-template runs/new-sample runs/请求目录/request.json
```

请求示例（路径换成真实项目路径，expected 来自模板原文）：

```json
{
  "template_path": "C:/实际项目/ppt-workflow/templates/imported/模板.pptx",
  "pages": [1, 4, 9],
  "edits": [
    {"slide": 1, "shape_id": 16, "expected": "工作总结汇报", "text": "模板复用验证"}
  ]
}
```

服务端真实工具 `create_wps_template_copy(request_path, output_dir)`。输出包括 request.json、template-adapted.pptx、slides/、wps-template.json 和 wps-readback.json。页号、对象 ID 指向原模板；改稿输出页序与 pages 对应。普通自动生成引擎仍为 unified-v3；本功能是既有模板的对象适配路径，不支持任意新布局生成或任意图表数据重写。

## 本次证据与限制

- `runs/wps-editing-20261017-001`：POTX实例化、ApplyTemplate、文字与流程组合形状、原生图表样式、表格保留、保存/重开/导图。
- `runs/wps-member-template-20261017-001`：已下载模板的真实 MCP 资源盘点。
- `runs/wps-template-adapted-20261017-006`：修复激活和文件占用后，MCP改稿、保存导图与十处文字独立回读完整成功。
- `runs/wps-template-review-20261017-001`：三张完整代表页，24处文字修改回读成功；环形图原始值0.40、0.14、0.15、0.31保留。接触表与artifact-verification.json在同目录。
- 图表数据只作模板示意，不作为业务事实。字体回退、跨机器字体以及其他模板仍需逐次检查。完整 OOXML schema 与所有编辑功能覆盖不在本次功能证明范围。
- 此模板详情标注“个人学习不支持商用”，仅用于本项目学习验证与样稿审核，已记录 source.json；通用工作流打包脚本排除 imported 内用户素材，不重新分发会员模板。
- 当前实际WPS注册路径产品版本12.1.0.26375；COM报告兼容版本14.0。旧记录12.1.0.28505不作为本次安装证据。

失败记录保留：同进程立即重开失效句柄、原文件打开引发占用提示、重复激活已有WPS返回忙。没有通过清空错误或停止全部后台进程来“修复”；改为物理快照、活动接口和独立进程回读。先前失败MCP记录不视为通过。
