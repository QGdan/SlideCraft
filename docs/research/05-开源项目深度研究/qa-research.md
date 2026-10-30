# PPT 验证、渲染与评估：一手资料研究及本地审计

研究日期：2026-10-13。范围：评估协议、渲染器、OOXML 与字体度量；只读审计 `02-工具链`、`skill/references` 及既有校准证据。本研究未安装依赖、未运行外部仓库代码、未重新调用 Office 渲染。文中的“本地实测”仅引用根代理运行的合成探针，明确区别于本研究的静态代码审阅。

## 1. 核心判断

高质量 PPT 需要四类证据：文件有效、结构可编辑、目标软件渲染可靠、内容和设计满足任务。任何单一总分或“lint 通过”都不能替代这四类证据。建议优先借鉴 PresentBench 的任务清单、Einsia PPTBench 的硬门禁与确定性扣分，以及 Open XML SDK 的格式验证；保留本地 linter 作为便宜的启发式预检，不能将其定位为 PowerPoint 排版的精确模拟器。

名称尤其需要核对：PPTAgent 的 PPTEval 不等于微软 PPT-Eval；PPTBench 至少有下文两项不同论文；SlideBench.org 与病理全切片图像 SlideBench 也不是同一项目。引用时应同时写作者仓库、论文编号、任务定义和版本。

## 2. 精选六项可借鉴项目

### 2.1 PPTAgent / PPTEval：分开评价内容、设计与连贯性

一手来源：[论文 2501.03936](https://arxiv.org/abs/2501.03936)、[v0.2.0 README](https://github.com/icip-cas/PPTAgent/tree/v0.2.0)、[MIT 许可](https://github.com/icip-cas/PPTAgent/blob/v0.2.0/LICENSE)、[当前仓库](https://github.com/icip-cas/PPTAgent)。

论文提出参考演示文稿分析、编辑式生成，并以 Content / Design / Coherence 三维 PPTEval 衡量输出；论文声称优于其对照方法，这是论文实验结论，尚未在本地复现。代码 MIT，数据和参考素材不能自动继承代码许可。当前 main 已转向 coding-agent skill 与外部视觉审核；仓库明确提示研究复现使用 v0.2.0，DeepPresenter 使用 v1.1.38。不能把 main 的技能功能当成 2025 论文实现或把论文成绩当成 main 的当前成绩。

适合借鉴：跨页叙事必须单独审；内容审应附源文档，设计审看全尺寸图像，避免以文字提取结果评价画面。缺点：三个维度仍需具体缺陷定位与人工校准；“综合评估”不是事实正确性、字号和可编辑性的证明。

### 2.2 PPTBench-Eval（Gastronomicluna，2512.02624）：版式理解与操作覆盖

一手来源：[论文 HTML](https://arxiv.org/html/2512.02624v1)、[仓库 README](https://github.com/Gastronomicluna/PPTBench-Eval)、[MIT LICENSE](https://github.com/Gastronomicluna/PPTBench-Eval/blob/main/LICENSE)。

论文从 958 个 PPTX 构建 4,439 个检测、理解、修改、生成样本；报告语义理解与空间版式能力之间的差距。README 有四条任务流水线、共享数据/模型工具、Hugging Face 数据集入口，生成另需图片资源包。开源代码为 MIT，数据集与素材仍须检查各自许可。此处核实的是论文与公开实现入口，未验证整套任务能在本机运行。

适合借鉴：建立“识别错误 → 描述关系 → 修改已有页 → 从头生成”的测试矩阵，不能只用生成成功率。限制：上述任务与中文整套答辩稿的美感、逻辑和资料可信度并不等价；958 是源文件数，不能写成 958 个生成测试。

### 2.3 PPTBench（Einsia，2609.29718）：硬门禁、结构问题与固定评分

一手来源：[论文](https://arxiv.org/abs/2609.29718)、[README](https://github.com/Einsia/PPTBench)、[评估协议](https://github.com/Einsia/PPTBench/blob/main/docs/evaluation.md)、[确定性评分源码](https://github.com/Einsia/PPTBench/blob/main/src/vlm_judge_harness/issue_ranker.py)、[三轮合并源码](https://github.com/Einsia/PPTBench/blob/main/src/vlm_judge_harness/consensus_ranker.py)、[数据许可](https://github.com/Einsia/PPTBench/blob/main/DATA_LICENSE.md)。

它考察 500 个科学图像的单页、原生可编辑对象重建，区别于上一项 PPTBench。README 固定 LibreOffice 25.8 为官方渲染条件；代码 MIT，项目元数据/标注/评审发现 CC BY 4.0，论文图像保留来源许可。任务下载核验原 PDF 和像素哈希，具有较强的材料版本控制。README 发布的模型成绩属于作者报告，未本地复现，不可外推整套商业或答辩 PPT。

协议把 artifact、连接方向/附着等语义、严重文字渲染错误作为门禁。三轮独立评审，任一硬门禁至少两轮失败时置零；随后模型输出缺陷而非分数，代码对布局30、文字40、局部图形30分应用固定扣分。静态阅读确认 `issue_ranker.py` 存在严重度及受影响比例阶梯，`consensus_ranker.py` 存在合并实现，但未执行。最值得移植的是“机器算分、视觉模型列证据”，不是原样复制一套针对科学图重建的权重。

### 2.4 PresentBench：源资料约束下的细粒度任务清单

一手来源：[论文 2603.07244](https://arxiv.org/abs/2603.07244)、[README](https://github.com/PresentBench/PresentBench)、[judge.py](https://github.com/PresentBench/PresentBench/blob/main/judge.py)、[Apache-2.0 LICENSE](https://github.com/PresentBench/PresentBench/blob/main/LICENSE)。

论文含 238 个实例，每例平均 54.1 项人工设计的二元清单，并报告较强的人类偏好一致性；这些是论文结论，不是本机独立验证。评估输入主要为 slides.pdf 和背景材料，故视觉高分不能证明 PPTX 可编辑。代码 Apache-2.0，下载数据须另核其数据卡。README 提供固定数据 revision 参数、单例及全量 judge、Poppler / PyMuPDF 渲染入口。

静态阅读 `judge.py` 可见：区分依赖资料与不依赖资料的评审项；每项有限重试（默认5）、指数退避、答案解析、定期保存和断点续跑；还提供 temperature / seed，但源码注释也承认后端未必完全确定。适合移植逐项证据与未完成状态。限制：API 失败须记录“未评估”，不可当通过；调用次数是清单规模乘重复评审次数，应显式限额。

### 2.5 Open XML SDK：真正的 OOXML 验证层

一手来源：[官方 README 与 MIT 声明](https://github.com/dotnet/Open-XML-SDK)、[OpenXmlValidator 实现](https://github.com/dotnet/Open-XML-SDK/blob/main/src/DocumentFormat.OpenXml.Framework/Validation/OpenXmlValidator.cs)。

SDK 提供 OPC、强类型 OOXML 与底层文档操作；`OpenXmlValidator` 可对包、部件、元素验证，且必须指定目标 Office 文件版本，默认 Office2007。它适合补足当前只靠 ZIP/正则的 `check`。许可 MIT。此处确认 API 与实现存在，没有本机编译或执行。

边界：格式/约束有效不代表图表表达正确、没有字号过小、文本溢出或渲染一致；还应检查外链、媒体引用、图表轴、原生对象数和资产来源。不能用 Schema validator 冒充视觉渲染器。

### 2.6 fontTools：字体资产和字形度量底座

一手来源：[TTFont 官方文档](https://fonttools.readthedocs.io/en/latest/ttLib/ttFont.html)、[代码 MIT 许可](https://github.com/fonttools/fonttools/blob/main/LICENSE)。

TTFont 支持解析字体表、cmap 和水平度量等，适合检查字体文件、字形覆盖、TTC 子字体、字体哈希，并提供布局估计数据。字体软件自身的许可独立于工具许可。它不是文本排版引擎：单独求和 hmtx 不实现字距调整、连字、复杂文字 shaping、禁则或 PowerPoint 的换行和字体回退。具体 fontTools 能力已核官方文档，未在本研究新跑度量。

本地实现已使用 fontTools，但以字形 advance 求和直接称为“exact metrics”应改为“字体表度量已匹配”；真正排版边界应由目标渲染器或经过独立校准的模型支持。

## 3. SlideBench 核查：可以学习方法，不能列为已核开源代码

[SlideBench.org 主页](https://www.slidebench.org/)和[方法页](https://www.slidebench.org/methodology)展示分类、两个任务轨道与可修改性维度；页面标注 GitHub coming soon。本次未核到可下载的官方实现与开源许可，不能作为开源工具推荐。其品牌工具排行榜也不能用于证明某个仓库的工程能力。网上另有病理 SlideBench 和同名金融页评测；应按 URL 与作者分开引用。此结论是“本次一手页面核查范围内未确认”，不是断言互联网上永远没有其代码。

## 4. 渲染层的可执行方案

PowerPoint COM 是目标用户使用桌面 Office 时的首选兼容性检查，但 Office 属于商业软件，COM 包装脚本开源不等于渲染器开源。[Slide.Export 官方 API](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slide.export)支持按像素宽高导出静态图片；[ExportAsFixedFormat](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentation.exportasfixedformat)支持静态 PDF/XPS。正确表述是“在记录的 Office 版本、字体与机器环境上的目标软件静态渲染”，不能无条件称 exact / ground truth：其他机器字体、Office build、放映动画、视频、动态链接和显示条件仍可能改变结果。

可另取 [TextRange.BoundHeight](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.textrange.boundheight) / [BoundWidth](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.textrange.boundwidth)，把目标软件计算的文字边界与文本框比较；它能加强溢出检查，但仍要处理旋转、组合变换和表格/图表自身的特殊文字。实施应由受控桌面 worker 执行，设置超时与进程归属，避免退出用户原有实例。

LibreOffice 为跨平台自动化路径；[官方参数文档](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)给出 `--headless`、`--convert-to`、`--outdir` 和独立 UserInstallation profile；[源码 MPL-2.0 许可文件](https://github.com/LibreOffice/core/blob/master/COPYING.MPL)可查。建议固定版本、字体镜像和 locale，以 PPTX→PDF→PNG 导出。LO 与 Office 差异要登记，不能自动裁定 LO 的警告是误报，也不能用“近似”排除真实缺陷。

建议每次写入独立 run 目录，而不是删改共用渲染目录；转换前记录输入 SHA256，渲染后验证 PNG 可读、维度、页数与文件哈希；没有任何 PNG 或页数缺失时必须失败。跨渲染器差异作为兼容性指标，人工复核高风险页，避免用像素一致性惩罚良好的字体替代。

## 5. 现有工具链审计：文档与代码的具体差距

证据级别：S=静态源码确认；H=现有历史文件；T=根代理本次合成实测。以下 T 引用 `05-开源项目深度研究/本地核查证据/audit-results.json`（方法明确为“没有新 PowerPoint 渲染”），源码为同目录 `local_audit.py`；不是生产样本成功率。

| 位置 | 发现与证据 | 后果 / 修正建议 |
|---|---|---|
| `deck_tools.py:171–182` | S：缺 pdftoppm 仅告知保留 PDF，然后返回0；pdftoppm 返回码被丢弃，未验证PNG数 | “render 成功”可以实际无预览。拆分 pdf_ok / images_ok，检查返回码和页数 |
| `deck_tools.py:132–179` | S：目录复用、不核输出时间/输入哈希；LO profile 固定为输出目录下同一子目录；所有 subprocess 无 timeout | 旧PDF/PNG可能冒充新结果；并行 profile 冲突。使用每次独立目录、唯一profile与有界超时 |
| `deck_tools.py:230–245` | S：注释称检查未声明axis id，实际只判断轴节点有无axId；部分正则结果未使用。T：引用999、仅声明1的合成ZIP仍exit0 | 只证明 checker 漏检，不是完整 PPTX 能正常打开。改用 XML 和 axId/crossAx 引用解析 |
| `deck_lint.py:311–433`、`:675` | S：只遍历顶层文字块，非文字shape收集后无边界检测，未递归group。T：画布外矩形及组内文字均0issues | “elements off-slide”承诺过宽。递归所有形状，并累计组变换 |
| `deck_lint.py:442–514` | S：长不可拆 token 即便比框宽仍只算一行，主要检测高度。T：120个W放入1in框得到0issues | 缺水平溢出门禁；探针未真实渲染。增加最长行宽检查与渲染器边界证据 |
| `deck_lint.py:565` | S：背景非None时首个fore_color读取不在try中。T：python-pptx继承背景触发NoFill TypeError | 合法输入也可使预检崩溃。完整解析继承链；未知背景应为unknown，不默认为可证明白色 |
| `fontmetrics.py:57–82` | S：缺字先计问号/空格advance，再加0.55em；没有设置approx；与校准文档“每字0.55em且标approx”不符 | 可能重复计宽且仍按2%严格度判断。返回本次字符串缺字状态，分离替代字宽策略 |
| `fontmetrics.py:86–117`、`:139–163` | S：只扫Windows字体目录；家庭名首遇文件胜出，无bold/italic选择；同字体对象缓存被修改approx/resolved_name | Linux合成回退；粗体度量不可靠；别名解析可能污染先前引用。建平台字体发现及style键，返回不可变解析结果 |
| `deck_lint.py:358–372` | S：`spcAft`被当pPr属性检查，实际读取路径又按子元素；点值行距`spcPts`未覆盖 | 常见段后间距漏算；按段落保存各自间距，不用全块最大值替代 |
| `deck_lint.py:485–540` | S：读取wrap但measure总会换行；fontScale仅在完整高度后乘，未重算缩小后的换行；ink_box称裁剪字形带但实际返回可用全宽/行高 | 横向/居中碰撞与autofit均可能误判。把模型标为启发式，必要时向COM边界核对 |
| `deck_lint.py:644–649` | S：代码MIN_CAPTION_PT=8，条件最终仅报<8pt；设计文档写任何文本9pt硬底线 | 8–9pt漏报，且混合字号被最大run合并后小字也可能消失。区分设计建议与真正执行规则 |
| `DESIGN-RULES.md:69` vs `deck_lint.py:575–606` | S：文档称只按slide背景比contrast，代码已经寻找实色底形/own_fill；但未正确限制底形须处于文字之前，且仅比明确srgb色 | 文档过时；主题色/渐变/图片背景覆盖不足。写明支持域，未知对比度不计通过 |
| `METRICS-CALIBRATION.md` | S/H：已明确group/table/chart/rotation盲区，值得保留；“GDI必然使用某行高”“无fontScale就不会自动缩小”等普适结论证据不足 | 只能归纳探针配置，不能扩展成Office所有版本规则；以actual bounds /渲染验证 |
| `balance_check.py` | S：最常见颜色视为背景；逐行像素阈值测band/gap | 是可解释的诊断，不是美感或“底部留白必定缺陷”判据；满屏照片/渐变/刻意留白容易误读 |
| `deck_tools.py:27–66` | S：dump按shape集合遍历，称reading order但未依据视觉/辅助功能顺序重排；notes截断400字符 | 不足以完整内容审与事实审；输出结构与完整notes，并核资料映射 |

`02-工具链/deck_lint.py` 与 `skill/scripts/deck_lint.py` 的 SHA256 一致，`fontmetrics.py` 两份也一致，所以上述问题同时影响技能脚本副本。

现有校准资产不是空承诺：`04-校准证据/make_probe.js`、`probe.pptx`、三页 PNG 和 `lint.json` 均存在；本研究查看第三页PNG，确有超出声明小文本框高度的长段落。可是 lint.json 保留旧目录路径和六条卡片误报，未记录当前源码hash、字体hash、渲染器build或测量程序；它是历史证据，不是当前代码完整回归报告。文档“约1%误差”仅限一个Calibri文本探针，不能当所有字体、内容与排版的误差上界。根代理本次10页demo预检0issues也只能说明该检查器在该输入上未发现其支持域内缺陷。

## 6. 推荐 QA 架构及交付清单

以下为本研究方案，尚未实现，不应写成现有能力。

```text
source manifest + task requirements + editable slide source
  → package/schema + asset/relationship checks
  → geometry/font/contrast heuristics（unknown 单独统计）
  → target-renderer export + output freshness/page-count gate
  → per-slide original image + suspicious-region crops + full-deck sheet
  → source-grounded checklist + visual findings JSON
  → deterministic gate/score + bounded repair + complete rerender
  → PPTX / PDF / PNG / QA evidence / known limitations
```

1. 包层：schema错误、无法打开、断裂内部关系、缺媒体、页数错误为硬失败；附字体、图片和参考模板许可证清单。可编辑性分别统计文字、连接线、表格、图表、矢量及允许的不可约照片，不能只看文件扩展名。
2. 布局层：组变换后对象越界、明确文本溢出、丢字为硬缺陷；允许预先标注的裁切背景和视觉包含关系。对比度、最小字号、背景/字体未知单列，不在未知时填“pass”。
3. 渲染层：产物页数/维度/可读性/哈希完整；记录Office或LO版本、font hashes、系统、locale、输入SHA256、渲染命令、退出码、elapsed、PNG/PDF hashes。所有失败留在分母中。
4. 内容层：每项任务要求一个可追踪问题，例如“单位是否与原表一致”“页3是否明确支持核心结论”，保存源文档页/段与幻灯片页/对象；不得把“总体看起来合理”转化为事实正确。
5. 视觉层：全页审字形、断行、局部图形；接触表审跨页风格、重复、节奏；复杂图表单独放大。JSON最少含slide、object/region、issue_type、severity、evidence、expected、actual、confidence、suggested_fix、status。模型列问题，代码汇总分数。

建议产品交付把硬失败数、未评估数与支持域放在总分之前；总分仅用于同任务、同工具链版本的比较。

## 7. 数据集、指标与有限重试

先建小规模、可重复的自有回归库，避免一开始跑付费大榜。建议首期24个微型deck：普通中文/英文/混排，缺字与字体替代、粗斜体、超长URL，段前后/点行距/百分比行距、禁则，wrap-off/autofit/旋转，组内文字/非文字越界，表格格内溢出，图表轴/图例，主题色/渐变/照片背景对比，4:3/16:9页比、截取背景、继承母版、多母版。每例包括好/坏对照和对象级真实标签，记录目标软件渲染；按模板拆分校准集与留出集，禁止同一页用于调阈值又报泛化。

外部数据分工：PPTBench-Eval 测空间/操作，Einsia 测可编辑科学图，PresentBench 测源资料和任务清单，PPTAgent/PPTEval 测跨页叙事；不要混成一个总榜。另保留用户真实中文答辩稿作为人工复核集，核可分发许可。

| 指标 | 可操作定义 | 不应误读 |
|---|---|---|
| Artifact/render success | 全部输入中可打开且输出页数完整的比例 | 不等于质量合格 |
| Critical-defect recall / precision | 人工标注严重溢出、缺字、越界中被检出的比例及误报比例 | 同时报样本数和置信区间，不能单报零问题 |
| Checklist completion / pass | 完成评审项/全项；通过项/全项，API失败单独记 | 不删除未评估项美化分母 |
| Editability coverage | 需编辑的语义对象中原生可编辑对象比例 | 截图+透明空框不能算可编辑 |
| Renderer disagreement | 同页两渲染器缺字/断行/边界的可解释差异 | SSIM/像素差仅为候选差异，不是美感评分 |
| Judge stability | 重复判定一致性、分歧页比例、与人工的一致性 | 同模型多轮并非真正独立裁判 |
| Repair utility/cost | 缺陷解决率、新增严重缺陷、迭代次数、wall time与API调用费 | 修复次数多不是效果好 |

建议限制：制作后最多2轮修复（初始+2次），每轮只修有定位证据的高严重度问题；修改后包检查、全量渲染和必要的视觉回归都要重跑。遇到无改善、来回抖动、新增严重缺陷或预算耗尽，恢复最佳已验证版本，交付已知限制。渲染基础设施失败最多1次环境重启重试；视觉API传输/格式失败每项最多3次含初次，指数退避加抖动，超时后标未评估，不触发无限内容重写。具体超时/成本上限按机器与deck大小配置，记录协议版本；这些上限是工程建议，不是引用项目默认值。

## 8. 视觉评审的盲区及文档降级措辞

缩略图掩盖小字、错字和箭头细节；VLM可能错读数字/公式/颜色、漏数重复对象，并偏好装饰精美但信息错误的页面。全页PNG无法证明对象可编辑、动画、辅助功能阅读顺序、演讲者备注或图表数据绑定。图像相似度可能奖励整页截图和错误的字形替代；复杂图形连接语义必须额外检查。多个同模型评审轮次仍可能共享偏差；应抽样人工审高分与低分，以及所有高风险内容页。

建议替换措辞：

- “COM 精确、ground truth” → “记录环境下的桌面PowerPoint静态导出，尚未验证其他环境或动态放映”。
- “预测PowerPoint如何排版” → “依据字体表和几何的启发式估计，覆盖普通顶层文本框”。
- “已校准，误差约1%” → “既有单一Calibri探针观察到约1%高度偏差，未建立跨字体误差界”。
- “check 验证PPTX” → “ZIP/部分关系快速检查；未替代OOXML schema与目标软件打开验证”。
- “0 issues、视觉验收完成” → “支持域内预检未发现问题；像素评审与内容核查分别列出是否完成”。

实施优先级：先修渲染成功条件与输出新鲜度，再补继承背景崩溃、全shape越界/组递归、水平文本溢出；随后修字体缺字状态/间距/字号一致性，接入格式验证器；最后增加结构化视觉评审与任务清单。这样每一步都能用小探针证明改进，避免先堆叠主观评分却保留工程假成功。
