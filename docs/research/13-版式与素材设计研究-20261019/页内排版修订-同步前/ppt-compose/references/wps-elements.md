# WPS 原生元素的实测使用路线

本机2026-10-17通过独立测试文稿验证。后台应用可以保留，优先活动应用接口；只创建自己的文稿，保存后用独立进程只读重开，避免退出共享WPS或修改用户其他文件。

| 元素/动作 | 已验证路线 | 边界 |
|---|---|---|
| 形状、文本、组合模块 | AddShape / AddTextbox → Group → Copy / Shapes.Paste → 修改组内文字 | Shape.Duplicate在本机返回对象但未写入保存文件，改用实际复制粘贴；保存后检查源组与副本 |
| 流程连接线 | AddConnector → BeginConnect / EndConnect | 重开核对两端仍连接，不能只画一条未绑定线冒充连接符 |
| 表格 | AddTable → 改写Cell文字 → 保存与回读 | 单元格保留为原生表格 |
| 模板原生图表模块 | 模板快照中Copy → 工作文稿Shapes.Paste → 修改ChartStyle | 原生图表与嵌入工作簿已验证保留；本机AddChart直接创建返回错误，不能承诺此接口可用 |
| SmartArt基本流程 | 从SmartArtLayouts选择“基本流程” → AddSmartArt → AllNodes改字 | 134种布局可枚举，只完整验证了基本流程；图片类布局的节点访问失败，不推定全库可编辑 |

SmartArt.Color赋值本机报错，不能声称全部样式控制已验证；需要统一配色时可用已验证的普通形状组合，或另测逐对象格式操作。WPS与PowerPoint能力分别验证，不能把某应用的SmartArt结果套给另一个应用。

再现测试：在绑定项目目录运行 `.mcp-venv/Scripts/python.exe scripts/verify_wps_elements.py runs/新的测试目录`。该脚本实际操作WPS；原生图表跨文稿复制部分依赖项目内已登记许可的 `templates/imported/WPS-Green-Report.pptx`，缺少时只记录未验证，不下载替代素材或伪造通过。

输出created.json与readback.json分别记录创建和重开结果，不能只看API未抛错。检查保存文件中的组子对象、连接端点、表格值、图表缓存/工作簿以及SmartArt数据部件。四页示例为功能验证，不构成业务PPT内容或整套设计批准。

Canva可作为后续补充设计工具，但本轮未完成Canva设计与PPTX导出验证。不能仅凭已安装或授权提示，就声称生成元素、导出后原生编辑性已打通；使用时按实际提供的工具与审批要求验证。
