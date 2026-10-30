# 扩展图表合同

过程、对照和行动信息图可调用项目ppt_workflow.exhibits.compose_exhibit，得到稳定ID的原生文字与连线对象，再并入spec；kind为process/comparison/action，输入title/body，action另需output。容量超限明确拒绝，不靠缩字号或装饰卡片填充。该组件输出对象仍须通过目标软件渲染检验，不保证任意长文本自动排版。

先运行python -m ppt_workflow capabilities。deck schema_version 0.2支持bar、column、line，最多12类别/4系列；布局合同可设置更低容量。pie/scatter/waterfall/map当前编译器明确拒绝，不静默转图。0.1读取兼容，旧统一构建入口保持原限制。

每张0.2图表提供semantics：task为comparison或trend，category_order为unordered或chronological，reason说明选型依据。折线必须声明同口径的时间序列；声明不是核验，仍需确认原始数据。

options可包含axis_min/axis_max/show_axis/show_legend/emphasize_categories/emphasize_series/label_format。轴需覆盖全部数据与零；百分比输入为0—100，默认显示使用带引号的百分号，避免把67.24显示成6724%。类别强调仅限单系列横条/柱图；多系列用系列强调。

quality-v1的0.2图表必须明确options.font_face及options.colors（accent/muted/ink，多系列另给series色数组或系列强调），所有值符合已批准模板。不要把默认青绿色混入用户的红黑或其他品牌模板。百分比默认0—100轴；其他单位按数据范围生成覆盖零和全部数据的尺度。

原生缓存、类别、系列、工作簿与图型分别检查。数据项继续绑定fact_ids。0.2百分比减法结果单位为百分点；不同scope文字的同一问题选项需显式comparison_group且同来源/同期，不能任意跨调查相减。comparison_group为人审声明，不能自动证明可比。

编译器与包检查通过，不代表Office渲染或交互保存已通过。默认模板的COM增强器对0.2图表保留编译时的颜色/类型，不再硬改成旧两类别样式。
