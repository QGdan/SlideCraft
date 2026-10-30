# 高质量 PPT 生成：Skill 与自动化工作流深度研究

> 研究日期：2026-02-14 · 环境：Windows 11 + Office 16.0.20430 + Node 24.11 + Python 3.12
> 结论先行：**难点不在"生成 pptx"，而在"生成后无法验证"**。本文给出可复现的验证方案与一套已跑通的工具链。

---

## 0. 摘要

制作高质量 PPT 的自动化，业界已从"调用 python-pptx 堆形状"演进到**三层分离架构**：

```
叙事层（写什么）  →  渲染层（怎么画）  →  验证层（画对了吗）
   大纲/标题党        pptxgenjs/OOXML       lint + 渲染 + 人眼
```

主流方案在**前两层**已经相当成熟，真正的空白和故障高发区是**第三层**。我做的核心工作是：**把第三层从"靠人眼看"变成"可计算、可复现、有基准"**，并用一次真实渲染实测校准了它的精度。

三个可直接复用的产出：

1. 一个能**预测 PowerPoint 文字溢出**的静态检查器（实测误差 ~1%）；
2. 一条**不依赖 LibreOffice** 的 Windows 原生渲染链路（PowerPoint COM）；
3. 一份把上述能力固化的 Skill：`~/.claude/skills/ppt-deck/`。

---

## 1. 研究方法与可信度声明

| 手段 | 覆盖 |
|---|---|
| 克隆并**逐行阅读** Anthropic 官方 `skills/pptx/SKILL.md`（238 行） | 一手，已核实 |
| 本地环境实测：pip / npm / COM / 字体 / 渲染 | 一手，已实测 |
| 4 个并行子代理做网络检索（skills 生态、工具链、设计规则） | 二手，已标注存疑项 |
| 端到端跑通：10 页中文 PPT → lint → 渲染 → 视觉验收 → 修正 → 复验 | 一手，已实测 |

**必须说明的两个环境约束：**

- 本会话**直接 HTTP 被阻断**（TLS 握手失败），只有 `web_search` 与 `git` 能出网。因此子代理的网络检索结果中，凡未能打开原文的结论我都标为**[存疑]**，不作为决策依据。核心结论均来自一手实测。
- **视觉验收走的是"委派"而非"本机"**：我自己的模型（`deepseek-flash`）不声明图像输入，直接调用 `read_image` 会被拒。但 `workflow` 工具支持**按子代理覆盖模型**，把模型换成 `deepseek-v4-flash-vision-exp` 就能真正读到像素。这个区别很关键——**"我这个模型没有视觉"不等于"这条链路没有视觉"**。我最初把结论下早了；修正过程本身产出了本文最有价值的发现（见 §5.4）。

---

## 2. 现状盘点：有哪些现成方案

### 2.1 Anthropic 官方 `pptx` skill —— 事实上的行业基线

仓库：<https://github.com/anthropics/skills>（`skills/pptx/`，已克隆并读完）

**它的三分路由（这是最关键的设计）：**

| 任务 | 官方指定做法 |
|---|---|
| 新建 | 写 `pptxgenjs` 脚本（**不是** python-pptx） |
| 改现有/套模板 | unzip → 改 `ppt/slides/slideN.xml` → zip |
| 读内容 | `markitdown`；看版式缩略图 `scripts/thumbnail.py` |

**它踩过的坑（官方逐条写明，含金量最高）：**

- pptxgenjs 默认画布是 **10×5.625 英寸**，不是 13.33×7.5；超出边界的形状**会被写入但不可见**。
- 颜色必须六位十六进制、**不带 `#`**；带 `#` 或八位带 alpha **会损坏文件**。
- `letterSpacing` 无效，真名是 `charSpacing`；选项对象**会被原地修改**，跨调用复用会串位。
- 阴影 `offset` **不可为负**，否则文件损坏。
- 堆叠柱状图 `dataLabelPosition: "outEnd"` **会损坏文件**。
- 双轴组合图若不同时给 `valAxes` 和 `catAxes` 各两项，PowerPoint 会**判定文件损坏并丢弃该图表**——而这个错误**能通过所有 XSD 校验**。

**它的设计规则（可直接沿用的硬约束）：**

- 每页必须有视觉元素；禁止"标题+项目符号"纯文字页。
- **严禁标题下划线 / 装饰色条 / 卡片单边描边**——这些是"AI 味"最强特征。
- 正文禁止居中；禁止 emoji；禁止米色系背景（`F5F5DC` 等）。
- 字体分"安全清单"与"QA 不可信清单"：Georgia/Impact/Consolas 等在 LibreOffice 里替代字体宽度不同，**溢出检查会误判**。

> **许可证（重要）**：`skills/pptx/LICENSE.txt` 明示 **"source-available, not open source"**，并禁止创建衍生作品、禁止在服务外保留副本。因此**我没有复制它的任何文本或代码**，本文仅作事实性引用。我的实现是独立完成的，依据是 OOXML 公开标准、WCAG 与我自己的实测数据。

### 2.2 第三方 skill 生态

检索到 20+ 个同类仓库，按架构可分四类：

| 类型 | 代表 | 评价 |
|---|---|---|
| 叙事/路由型 | `gnipbao/knowledge-cat-ppt-skill`、`SlideSpeak/slide-design-skill` | 强调"先故事后排版"，输出 HTML 而非 pptx |
| JSON 中间层 | `jinwyp/open-ppt-skill`、`siril9/presentation-skill` | 声明"从 JSON 重建 + 渲染式视觉 QA"，架构与我最终选择一致 |
| 限界声明型 | `Ronnie2025/codex-ppt-skill`（自带 `references/limitations.md`） | **唯一主动写失败清单的**，思路值得学 |
| 官方/厂商型 | `JetBrains/skills` 的 `slides/` | 体积小，可做对照 |

**结论：这些仓库的价值主要是"清单"而非"实现"。** 它们普遍只到"渲染出来看一眼"，没有一个给出可量化的溢出判定。**[存疑]**：以上仓库内容我未能逐一打开，仅依据元数据与检索摘要。

### 2.3 MCP 服务器

| 服务器 | 架构 | 关键限制 |
|---|---|---|
| `GongRzhe/Office-PowerPoint-MCP-Server` | python-pptx | **无法渲染 → 无法视觉验证** |
| `IBM/chuk-mcp-pptx` | python-pptx | 同上 |
| `xintian-lab/ppt-mcp`、`ykuwai/ppt-mcp` | **驱动真实 PowerPoint（COM）** | 需装 Office、有状态、难并发；`ykuwai` 自称 156 个工具，**工具数膨胀本身是设计坏味道**——上下文成本极高 |

**关键判断**：MCP 把能力暴露成工具，但**工具数 ≠ 质量**。一个 10 页 PPT 需要几十次工具往返，而一个 skill 让模型直接写一个生成脚本，一次成型。**对"做 PPT"这个任务，skill 优于 MCP。**

### 2.4 商业/其他库

| 库 | 优势 | 代价 |
|---|---|---|
| **Aspose.Slides** | 保真度最高，支持动画/切换/字体嵌入/自带渲染 | 商业授权 |
| **PptxGenJS** | MIT、原生母版、原生图表、原生表格 | **不能编辑已有 pptx**（设计上只能生成） |
| **python-pptx 1.0.2** | 纯 Python、可读可写、`Chart.replace_data()` 换数据不丢格式 | **无自动缩放计算**（issue #973/#969）、无 SmartArt、无动画、无法插入 SVG/EMF |
| **Apache POI XSLF** | Apache-2.0 | `createChart()` 缺失 |

**python-pptx 的自动缩放是个陷阱**：它能设置 `TEXT_TO_FIT_SHAPE` 属性，但**不会计算缩放后的字号**——那是 PowerPoint 布局引擎的活。所以"开了自动缩放"≠"不会溢出"，**打开文件时仍然是溢出的**。

---

## 3. 实测：文字溢出的可计算化（本文核心）

### 3.1 为什么必须做这件事

"文字溢出"是 AI 生成 PPT 的**头号可见缺陷**，且是**唯一无法靠格式校验发现**的缺陷——文件完全合法，XSD 全过，LibreOffice 也能渲染，但人一打开就看到文字戳出框外。

### 3.2 模型：三个量必须准

```
可用宽度 = 框宽 − lIns − rIns          （OOXML 默认左右各 0.1 英寸）
行高     = (usWinAscent + usWinDescent) / unitsPerEm × 字号
文字高度 = 行数 × 行高
```

### 3.3 踩的第一个坑：行高公式

初版实现把 `OS/2.sTypoLineGap` 也加进了 descent，得到 Calibri 行高比 **1.4414**。

**这是错的**——`sTypoLineGap` 本身就是行间留白，GDI（以及 PowerPoint）用的是 `usWin*` 那一对，重复计算了。

修正后：Calibri = `(1950+550)/2048 = ` **1.2207**。

### 3.4 校准：跟真实渲染对账

构造探针：16pt Calibri 正文放进 **4.00 × 1.00 英寸**的框（故意溢出），用 **PowerPoint COM 导出 1920×1080 PNG（144 px/in）**，再逐行做像素分析。

| 指标 | 像素实测 | 模型预测 | 误差 |
|---|---|---|---|
| 行距 | 38–39 px = 0.2674 in | 0.2713 in | **+1.4%** |
| 文字块总高 | ~349 px = 2.42 in | **2.44 in** | **+0.8%** |
| 折行数 | 9 行 | **9 行** | **0%** |
| 列宽占用 | ≤4.00 in（未越界） | 4.00 in | 0% |

**模型故意偏高**（宁误报不漏报）——因为漏报的溢出是用户直接能看见的缺陷，误报只是多跑一次修正。

### 3.5 踩的第二个坑：溢出位置算错

文本框的**声明矩形不是文字实际落点**。垂直锚点会移动它：

```
slack = 可用高 − 内容高
anchor=ctr → 顶部 = 框顶 + tIns + slack/2
anchor=b   → 顶部 = 框顶 + tIns + slack
```

探针页用的是 `anchor="ctr"`，实测文字**同时溢出框顶和框底**。初版碰撞检测用声明矩形，结果在一页 KPI 卡片上**误报 6 处碰撞**（大数字本来就该在卡片里居中）。

改为按**计算出的"墨迹框"**做碰撞检测后，误报归零。

### 3.6 踩的第三个坑：容差不能只有百分比

早期用"超出 2% 即报错"。结果每个 11pt 小标签框（框高 0.26 in，文字需 0.33 in）都报错——**27% 超标，但视觉上完全看不出**，因为行高本身就会超出窄框。

修正：**相对容差与绝对容差必须同时满足**。

```python
if h_used > avail_h * (1 + tol) and (h_used - avail_h) > 0.08:   # 0.08 英寸
```

探针页 1.44 in 的溢出**照抓不误**，小标签误报全部消失。

### 3.7 容差策略

| 条件 | 容差 | 理由 |
|---|---|---|
| 字体已安装、字形齐全 | 2% | 度量精确 |
| 字体被替代或字形缺失 | 10% | 替代字体宽度不同，降级为 warning |

---

## 4. 渲染链路：Windows 上与官方方案的差异

### 4.1 官方方案在本机不可用

Anthropic 的 QA 链路是 `LibreOffice → PDF → pdftoppm → PNG`。**本机没有 LibreOffice**（有 WPS，但无可靠 CLI 导出）。

### 4.2 改用 PowerPoint COM —— 反而更好

```powershell
$app  = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($Pptx, $true, $false, $false)  # ReadOnly,!Untitled,!WithWindow
$pres.Slides.Item($i).Export($file, "PNG", 1600, 900)          # 像素尺寸
```

实测（Office 16.0.20430）：

- `Presentations.Open` **四个位置参数**，只传文件名会弹出可见窗口并残留进程。
- **必须在 `finally` 里 `Quit()` 并释放 COM 对象**——残留的 `POWERPNT.EXE` 会锁住文件，导致下次生成失败，症状很像"权限问题"。
- **中文渲染正确**：探针页的"微软雅黑正文测试"导出为**真实完整字形**，非豆腐块（已逐像素确认 busiest row 有 59 段墨迹，符合汉字笔画结构）。

**关键优势**：官方用 LibreOffice 时，字体替代会让预览出现"真实环境中不存在的溢出"，所以它不得不维护"QA 不可信字体清单"并留 10% 余量。**用 PowerPoint 渲染 = 所见即所得，不需要这份妥协。** 代价是必须装桌面版 Office。

---

## 5. 端到端验证：10 页中文 PPT

生成器 `examples/make_demo_zh.js`（教学数据分析平台汇报），跑完整链路：

```
pptxgenjs 生成 → deck_lint 静态检查 → PowerPoint COM 渲染 → 接触表 + 像素分析
```

### 5.1 linter 抓到的真实缺陷（不是误报）

首轮 **20 errors**。逐项归因后，**8 项是设计真实缺陷**：

| 问题 | 数据 | 处置 |
|---|---|---|
| 小字对比度不足 | `#D97706` 橙 on 白 = **3.2:1** < 4.5:1 | 新增 `accentText: #A85B04`（5.2:1）专供小字 |
| 白字在橙圆上 | **3.0:1** < 4.5:1 | 圆圈底色改深青 `#0B3C49`（9.8:1） |
| 次级文字在卡片上 | `#5C7480` on `#EFF4F5` = **4.4:1** | 改 `#546A75`（4.9:1） |

**注意**：这三项在原设计里"看起来没问题"——浅灰字在浅灰卡片上，肉眼很难判断 4.4 和 4.5 的差别。**这正是程序化检查的意义：把审美判断变成可计算的阈值。**

### 5.2 我自己的 linter 也出了 4 个 bug（已修）

| Bug | 症状 | 根因 |
|---|---|---|
| 行高多算 18% | 校准阶段发现 | 重复计算 `sTypoLineGap` |
| 颜色读不到 | 对比度全部按"默认色"判 | 用 `font.color.rgb` 读，应从 `a:rPr/a:solidFill/a:srgbClr` 直接解析 |
| 实心形状填充读不到 | 白字被判 1.0:1 | `str(fill.type)` 是 `"SOLID (1)"`，与 `"MSO_FILL_TYPE.SOLID"` 比较**永远为假** |
| 空文本框被当文字块 | 装饰线被报"溢出" | 无字符的 frame 也进了测量流程 |

**这四条都写进了代码注释**，避免回归。

### 5.3 最终结果

```
demo-zh.pptx: 10 slides, 0 error(s), 0 warning(s)
OK   demo-zh.pptx  ·  10 slide part(s)  ·  1 native chart(s)
```

渲染 10 张 1600×900 PNG 全部成功。像素分析确认版式多样性：

| 页 | 主色 | 墨迹占比 | 判定 |
|---|---|---|---|
| 1 封面 | `#072A33` | 2.4% | 深色封面 ✓ |
| 4 KPI 卡 | `#FFFFFF` + `#EFF4F5` | **30.9%** | 卡片与文字已渲染 ✓ |
| 6 图表页 | `#FFFFFF` + 橙 `#D97706` | 23.6% | 图表 + 橙色强调已渲染 ✓ |
| 3/5/7 分节 | `#0B3C49` | 1.0% | 深色分节页，节奏变化 ✓ |

**节奏检查通过**：不是"每页都是标题+列表"的同质化版式。

### 5.4 视觉验收推翻了 lint 的结论（本文最有价值的发现）

用 `workflow` 把模型覆盖为 `deepseek-v4-flash-vision-exp` 后，视觉验收真的跑起来了。**它发现的缺陷，我的 linter 一个都没报——而那一版是 `0 error / 0 warning`。**

| 缺陷 | 视觉验收原话 | linter 为何看不见 |
|---|---|---|
| 图表"试点前"数据系列几乎不可见 | "light blue-gray bars are only slightly darker than the white slide background" | 只检查**文字**对比度，不检查**图形**对比度（WCAG 1.4.11 要求 3:1） |
| 标注框折行难看 | 把 `（+19` 与 `分）` 拆到两行、把 `针对性` 拦腰截断 | 折行数算对了，但**"折在哪"根本不是几何问题** |
| 第 4、6、8、9 页底部大片留白 | "roughly the lower third is blank"、"bottom whitespace ≈ 50%" | 只判断**元素是否越界**，不判断**留白是否失衡** |

**量化验证**：我随后写了 `balance_check.py`（逐行墨迹剖面）复测，确认视觉判断准确——第 8 页底部空 50%、第 4 页内容块只占上部 65%。

**结论：lint 通过 ≠ 版面合格。** 二者检查的是**不相交**的缺陷集合：

- linter 擅长：**可判定**的违规（越界、碰撞、阈值不足）
- 视觉擅长：**需要审美判断**的问题（留白失衡、折行难看、视觉重心）

**任何一个单独用都不够。** 这条结论修正了我研究初期的方案设计——原本我以为"把溢出算准"就解决了验证问题，实际上只解决了一半。

### 5.5 修正：一个自己写出来的回归 bug

按视觉反馈修垂直平衡时，我写了 `recenterContent()`：把每页内容块整体下移到底部留白与顶部留白相等。

**第一版错得很难看**：我按"元素类型"给每个对象单独设了下移上限，结果**卡片下移了、卡片里的数字没下移**——内容块被撕开。linter 立刻报出 **56 个碰撞警告**。

这个 bug 有教育意义：**修版式的代码本身会引入版式缺陷，而只有"改完立刻重新 lint"才能发现。** 修正为"先算出一个统一的位移量、再整体应用"后归零。

第二版仍不理想：最大化居中导致标题与第一条内容之间出现 **1.70 英寸空洞**（`geom.py` 实测），比底部留白更难看。最终约束为"内容起始位置不得低于标题下方 0.9 英寸"，用几何导出逐轮核对：

| 迭代 | 第 2 页标题→内容间距 | 第 2 页底部留白 | 第 4 页底部留白 |
|---|---|---|---|
| 修前 | 1.70 in | ~40% | ~40% |
| 居中版 | 0.77 in | 33.4% | 4.4% |
| **最终版** | **0.77 in** | **21.4%** | **4.6%** |

**"留白多少算失衡"没有客观阈值**——这是审美判断，只能靠看。但它可以被**测量**（`balance_check.py`），从而让"改一次、量一次"变成可迭代的流程，而不是凭感觉反复调。

---

## 6. 推荐架构（本文结论）

| 层 | 选择 | 理由 |
|---|---|---|
| **内容层** | 先出"标题清单"给人确认 | 结构改起来比版式贵得多 |
| **生成层** | **pptxgenjs**（新建） / **OOXML 直接改**（套模板） | 原生母版+原生图表；官方同款选择 |
| **验证层** | **linter + 真实渲染 + 视觉模型 + 平衡测量** | 这是现有方案最大的空白，且需要四件套而非单件 |

### 6.1 九条最有价值的经验

1. **把"溢出"变成可计算量**——这是唯一无法靠 schema 校验发现、又必然被人眼看到的缺陷。
2. **lint 与视觉检查的是不相交的缺陷集合**（§5.4 实测）：linter 管可判定的违规，视觉管需要审美判断的失衡。**两者都不可省。**
3. **"自己没有视觉"要先验证再说**——先确认工具链里有没有可覆盖视觉模型的通道，再下"无法验收"的结论。我在这上面判断错过一次。
4. **不要用 PowerPoint 自动缩放当溢出解药**：它不重算字号，打开时照样溢出，还会把 18pt 悄悄变成 11pt。
5. **修版式的代码会引入版式缺陷**：我的居中函数第一版把卡片和卡片里的文字拆开了，linter 报 56 个碰撞。**改完立刻重新 lint** 是唯一防线。
6. **留白可以用像素测量**（`balance_check.py`），即使"多少算失衡"仍是审美判断——可测量就能迭代。
7. **设计规则要写成阈值**：4.5:1、0.3 英寸、2% 容差。写成"要美观"等于没写。
8. **字体是指纹**：报错说"字体没装"比"版面错位"有用得多——错位的根因通常是字体替代。
9. **生成器必须可重跑**：内容放数组、版式放函数。lint 报错后是改生成器重跑，**不是手工改 XML**。

### 6.2 明确的能力边界（不要过度承诺）

- 折行是**贪心算法**，未实现 PowerPoint 完整的禁则处理（中文逐字断行除外）。
- **SmartArt / WordArt / 组合形状内的文字不测量。**
- **表格单元格溢出不检查**，图表轴标签碰撞检查不到——这些只能靠眼睛。
- 旋转文字按未旋转测量，可能误判。
- 未安装字体时用的是替代字体度量，只是**近似**。

---

## 7. 交付物与用法

### 7.1 已安装

```
~/.claude/skills/ppt-deck/
├── SKILL.md                          # 工作流主文档（7 步）
├── references/
│   ├── DESIGN-RULES.md               # 每条阈值 + 来源标注（[std]/[共识]/[实测]）
│   ├── METRICS-CALIBRATION.md        # 度量模型如何校准、误差多少、已知局限
│   └── RENDERING.md                  # 各渲染器取舍与平台坑
├── scripts/
│   ├── deck_lint.py                  # 静态预检：溢出/越界/碰撞/对比度/字体/占位符/emoji
│   ├── deck_tools.py                 # dump / render / sheets / check 四个子命令
│   ├── fontmetrics.py                # 字体解析与度量（可直接查某字体替代成了什么）
│   └── render_windows.ps1            # PowerPoint COM 渲染器
└── examples/
    ├── make_demo_zh.js               # 参考生成器（10 页中文，含注释）
    └── demo-zh.pptx                  # 已通过检查的成品
```

### 7.2 四条命令

```bash
python scripts/deck_lint.py deck.pptx --json lint.json   # 退出码 1 = 有 error
python scripts/deck_tools.py dump deck.pptx              # 按阅读顺序取文字，查内容
python scripts/deck_tools.py render deck.pptx out/ --width 1600 --height 900
python scripts/deck_tools.py sheets out/ --prefix contact # 6 页一张接触表
python scripts/deck_tools.py check deck.pptx             # OPC 包/关系/图表轴合法性
```

### 7.3 依赖

```bash
pip install python-pptx Pillow fonttools defusedxml
npm install pptxgenjs            # npm 报权限错就加：--cache ./.npm-cache
```

渲染需要桌面版 PowerPoint（Windows）或 LibreOffice + `pdftoppm`。

---

## 8. 给你的三条路线建议

| 你的场景 | 建议 |
|---|---|
| **要快、要好、能改** | 直接用已装好的 `ppt-deck` skill：给主题 → 我出标题清单 → 你确认 → 生成 → lint → 渲染 → 你验收 |
| **要套学院/大赛模板** | 走"模板复用"路线（SKILL.md 第 6 步）：把你现有的 `.pptx` 给我，我读它的配色/字体/版式，**只填内容不重造样式**。你桌面的 `国赛模板`、`计算机设计大赛`、`参赛作品` 可以直接用 |
| **要完全自己掌控** | 照 `examples/make_demo_zh.js` 改：内容放数组，版式放函数，每次改完跑 lint + render |

**关于你已装的官方 skill**：Anthropic 的 `pptx` skill 如果在本机装过，会遇到两个不适配——(a) 它假设 `pptxgenjs` 与 LibreOffice 已预装，本机都没有；(b) 它的 QA 依赖 `soffice` + `pdftoppm`，本机缺 `soffice`。本方案专门解决了这两点。

---

## 9. 一句话结论

**做高质量 PPT 的自动化，瓶颈从来不是"不会画"，而是"画完不知道对不对"。**
现成 skill 和 MCP 都把力气花在生成上，我把力气花在**验证**上——把溢出变成可计算的数，把渲染换成与演讲者同一套引擎，把设计规则写成可执行的阈值。这三件事做完，PPT 自动化的可靠性才从"碰运气"变成"可回归"。

---

## 10. 来源

**一手（已克隆/已实测）**
- Anthropic 官方技能仓库：<https://github.com/anthropics/skills>（`skills/pptx/`，许可证：source-available，禁止衍生）
- [PptxGenJS](https://github.com/gitbrent/PptxGenJS) · [python-pptx](https://github.com/scanny/python-pptx)
- python-pptx 自动缩放限制：[issue #973](https://github.com/scanny/python-pptx/issues/973)、[#969](https://github.com/scanny/python-pptx/issues/969)
- 本机实测：Office 16.0.20430、PowerPoint COM 导出、字体 `msyh.ttc`/`calibri.ttf` 度量

**标准**
- [WCAG 2.1 SC 1.4.3 / 1.4.11](https://www.w3.org/TR/WCAG21/)（对比度 4.5:1 / 3:1）
- [ECMA-376 / ISO-IEC 29500](https://www.ecma-international.org/publications-and-standards/standards/ecma-376/)（OOXML DrawingML 文本度量）
- [Agent Skills 规范](https://agentskills.io/specification)

**二手（检索所得，[存疑] 者未采纳为结论）**
- [cosen1024/awesome-presentation-skills](https://github.com/cosen1024/awesome-presentation-skills)、[ningzimu/awesome-ai-ppt](https://github.com/ningzimu/awesome-ai-ppt)
- [gnipbao/knowledge-cat-ppt-skill](https://github.com/gnipbao/knowledge-cat-ppt-skill)、[siril9/presentation-skill](https://github.com/siril9/presentation-skill)、[Ronnie2025/codex-ppt-skill](https://github.com/Ronnie2025/codex-ppt-skill)
- [GongRzhe/Office-PowerPoint-MCP-Server](https://github.com/gongrzhe/Office-PowerPoint-MCP-Server)、[IBM/chuk-mcp-pptx](https://github.com/IBM/chuk-mcp-pptx)
- 设计理论：Minto 金字塔原理、Duarte sparkline、Alley assertion–evidence、FT Visual Vocabulary
