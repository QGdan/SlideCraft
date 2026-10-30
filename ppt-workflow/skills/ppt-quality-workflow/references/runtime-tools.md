# 工具与连接入口

本机2026-10-19存在Python→PowerShell导图启动链失败，而直接PowerShell调用成功的差异。按项目docs/Office直接导图与连接恢复.md使用 `scripts/render_direct.ps1` 备用入口并核对render-manifest.json；不能从Python再次启动该入口来冒充已验证路线。WPS在activate阶段失败时可直接执行activate_wps.ps1只读激活，connected后将原MCP请求用新目录重试一次；仍失败则停止该恢复路径。保留用户会话、原互斥/隔离锁和真实批准，不改全局配置。

先从相邻runtime.json解析项目根。在项目中运行 `.venv/Scripts/python.exe -m ppt_workflow doctor`，再运行 `.mcp-venv/Scripts/python.exe scripts/office_mcp_client.py health runs/new-health-check`。输出目录必须不存在；health真实握手并列出服务端工具，但不打开Office。

主线MCP服务通过stdio启动，命令为项目 `.mcp-venv/Scripts/python.exe office-mcp/server.py`，cwd为项目根。不需要HTTP地址或API key；没有因此自动注册到宿主全局MCP工具列表。制作命令内部已经通过该客户端调用，不能另外假设有一个同名远端工具。

| 客户端operation | 服务工具 | 输入 |
|---|---|---|
| health | health_check | 新输出目录；无Office操作 |
| catalog | catalog_native_features | 新输出目录 |
| inspect-template | inspect_template_resources | 新输出目录、真实 POTX/PPTX；仅读文件，不启动 Office |
| wps-health | probe_wps_connection | runs 下新输出目录；允许后台进程，仅读应用版本和文稿数量，不退出 WPS |
| wps-template | create_wps_template_copy | runs 下新输出目录、项目内请求JSON；模板路径、选定页与expected校验的文字修改 |

WPS 模板请求与实测范围见绑定项目 `docs/WPS-模板工作流.md`。会员库选择/下载经桌面界面完成，MCP 负责本地模板盘点和副本改稿，不存在已验证的商城搜索 API。先物理快照再操作，优先活动应用接口，保存后独立进程回读；不要求关闭用户后台进程，也不 Quit 共享应用。
| unified-template | create_unified_template | 新输出目录 |
| instantiate | create_from_template | 新输出目录、真实POTX路径 |
| enhance | apply_editorial_design | 新输出目录、含normalized.pptx/deck-spec.json的输入目录 |

只有真实worker返回completed且cleanupCompleted为true，才说明该Office操作成功；doctor注册表存在不能代替COM实测。已有用户PowerPoint会话时拒绝接管。SmartArt取决于软件可用性，统一主线采用原生组合形状。

Figma：先查询当前工具及认证，再加载宿主提供的figma-use/figma-use-slides指引，读取实际目标文件。Slides不可使用只支持Design的get_metadata。认证成功不等于某文件可写或Figma→PPTX往返已验证。

在线PowerPoint：如宿主提供Document Control，先list_document_sessions(surface="powerpoint")；有会话后读取对应get_document_tool_schemas，再按实际工具名和参数执行。空列表表示无连接，不能用不存在的session ID。WPS基础只读查询已通过项目stdio MCP实测，不要求关闭后台进程；它没有调用Quit，也不改动用户文档。后续已验证模板副本编辑、保存、导图、独立回读及会员界面下载；具体范围见WPS模板工作流，不表示全部编辑功能或商城API已支持。

生图：加载当时可用的imagegen Skill并调用宿主实际提供的工具。当前主线能使用登记好的本地图像，没有内置OpenAI HTTP调用、API key或固定Image2模型参数；不为连接自检额外生成收费图片。模型未暴露时按未暴露记录。PNG保持位图，原生编辑需求交制作Skill做语义重建。

完整当前连接记录和官方文档链接见绑定项目的docs/工具与连接.md。过去的认证、文件截图和审核记录仅为当时证据，外部工具在执行任务时仍需重新检查。
