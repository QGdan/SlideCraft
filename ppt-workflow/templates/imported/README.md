# 导入用户模板

把你选择且有权使用的 PowerPoint/WPS 模板放在此处，格式为 `.potx` 或 `.pptx`。WPS 的 `.dps` 请先另存为 `.pptx`。

在 ppt-workflow 目录运行：

```powershell
.\.mcp-venv\Scripts\python.exe scripts/office_mcp_client.py inspect-template runs/my-template-check templates/imported/我的模板.pptx
```

输出目录必须尚不存在。工具只盘点母版、布局、主题字体/颜色、占位符与对象 ID，不更改原文件，不启动 Office，不自动下载商城模板。接着由 ppt-template 制作三张代表样页，用户审核后交 ppt-compose 进行模板适配。当前默认 unified-v3 引擎没有因此自动兼容任意外部模板。
