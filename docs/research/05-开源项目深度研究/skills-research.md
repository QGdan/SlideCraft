# AI agent skill、代码驱动设计与网页幻灯片：一手证据核查

核查日期：2026-10-13。范围：7 项；只读 GitHub 源码和官方文档，未安装依赖、未执行项目代码。以下“支持”表示源码/文档证据，不表示本机实测成功。GitHub 部分页面来自搜索缓存；不把缓存显示的最后一条提交当成当前最后提交。

## 结论先行

可编辑 PPTX 的主线建议：以 **OpenAI slides 固定历史提交的 Apache-2.0 工具**为候选底座，或以 PptxGenJS 独立实现同类验收；借鉴 MiniMax 的模块化页合同；加入自己的中文字体、模板和内容真实性约束。OpenAI 的历史目录已从 main 删除，必须固定版本并保留许可，不能称为当前官方安装入口。[删除记录](https://github.com/openai/skills/commits/main/)、[历史 skill](https://github.com/openai/skills/tree/e6afb0d74cc75d220df2faf3dd6c635c2dc6a108/skills/.curated/slides)

网页主线建议：**Frontend Slides** 用于风格发现和 HTML 演示；**Marp** 用于 Markdown、CSS 主题和批量交付；**Slidev** 用于代码、交互、复杂技术演讲。Marp/Slidev 常规 PPTX 是整页图片，但两者现在都有额外的可编辑导出模式，不能再一概断言“不支持可编辑 PPTX”。可编辑模式均需要专项保真验收。[Marp 导出](https://github.com/marp-team/marp-cli#convert-to-powerpoint-document---pptx-)、[Slidev 导出](https://sli.dev/guide/exporting)

**Anthropic pptx 不纳入可复用开源底座。** 其当前文件级许可仍写明禁止衍生等限制；此前报告这个判断成立，纠错对象应是“Anthropic 整个 skills 仓库都 Apache-2.0”这一概括。[当前文件级许可证](https://github.com/anthropics/skills/blob/main/skills/pptx/LICENSE.txt)

## 路线对照

| 项目/版本范围 | 实际产物 | 可编辑边界 | 许可证据 | 本研究建议 |
|---|---|---|---|---|
| Anthropic skills/pptx，main | 原生元素 PPTX；模板 XML 编辑 | 强调原生图表；图片仍是图片 | 文件夹内 Proprietary | 仅作公开能力对照，不复制提示词/脚本 |
| OpenAI slides，固定 e6afb0d… | JS＋可编辑 PPTX＋渲染图 | 文本、简单图表原生；复杂图形 SVG | 文件夹内 Apache-2.0 | 可编辑主线候选，版本冻结 |
| JetBrains/skills/slides，main | JS＋PPTX＋渲染图 | 同类原生元素路线 | 文件夹内 Apache-2.0 | 当前可获取的迁移版本，非新算法 |
| MiniMax pptx-generator，main | agent 生成分页面 JS＋汇总 PPTX | PptxGenJS 原生元素/XML 模板编辑 | 根 MIT＋skill frontmatter MIT | 模块合同和中文规范参考 |
| zarazhangrui/frontend-slides，main | HTML；截图式 PDF | HTML 文字可改；没有原生 PPTX 导出承诺 | 根 MIT | 风格预览与网页路线 |
| Marp CLI，官方 README/main | HTML、PDF、图片 PPTX；实验可编辑 PPTX | 默认整图；实验转换可能失真 | MIT | 低成本可复现基线 |
| Slidev，v52.20.0 起的新导出/当前文档 | Web、PDF、图片 PPTX、可编辑 PPTX | 可编辑模式重建文本/形状，复杂元素图片化 | MIT | 新增对照试验，监控逐页回退 |

表中许可链接和版本依据见各项目小节；外部图片、字体、模板和依赖各自的许可仍需单独记录，根许可证不自动覆盖外部素材。

## 1. Anthropic skills/pptx：源可见，不是可自由衍生的 skill

一手材料：[SKILL.md](https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md)、[LICENSE.txt](https://github.com/anthropics/skills/blob/main/skills/pptx/LICENSE.txt)。本次读取 raw main，文件正文仍为 Proprietary；限制覆盖代码、提示词、资产及其他组件。关键原文仅引一项：`Create derivative works based on these materials`。它属于禁止项，此外还有留存、复制、分发限制。这里是文件条款核查，不扩张推断其生成用户内容的所有权。

实现：新建走 PptxGenJS；既有模板走 OOXML 解包、修改和重打包；包含 thumbnail、add_slide、clean、office/validate、soffice 包装工具。验收既有内容提取，也有包结构/关系/图表检查和全分辨率渲染。模板编辑先定页型和结构，再替换内容；重复页不自动独立复制图表等关联部件，这是实际工程边界。[实现入口](https://raw.githubusercontent.com/anthropics/skills/main/skills/pptx/SKILL.md)

维护信号：当前文件可读、流程涵盖 `.potx` 和图表故障；本次没有固定其 main SHA 或核实最近提交日期。结论：能说明商业平台 skill 的成熟度，但不能直接收进本地开源改造计划。

## 2. OpenAI slides：固定历史版本有完整 helper，不等于当前 main

一手材料：[固定版本 SKILL.md](https://raw.githubusercontent.com/openai/skills/e6afb0d74cc75d220df2faf3dd6c635c2dc6a108/skills/.curated/slides/SKILL.md)、[同目录 Apache-2.0 LICENSE.txt](https://raw.githubusercontent.com/openai/skills/e6afb0d74cc75d220df2faf3dd6c635c2dc6a108/skills/.curated/slides/LICENSE.txt)。[官方提交历史](https://github.com/openai/skills/commits/main/)记录 2026-04-16 的 `Remove spreadsheets and slides skills (#350)`；因此必须用固定提交检索，不能把历史内容当成 main 当前推荐。

实现：PptxGenJS 生成、交付 `.pptx` 和 `.js`，尺寸和字体显式指定。`assets/pptxgenjs_helpers` 分装文本、图片、SVG、LaTeX、代码、布局等模块；[index.js](https://raw.githubusercontent.com/openai/skills/e6afb0d74cc75d220df2faf3dd6c635c2dc6a108/skills/.curated/slides/assets/pptxgenjs_helpers/index.js) 可核查 VERSION 1.2.0 和真实导出。提示词要求生成器含重叠/越界告警，文本留为文本、简单图表尽量原生。

验收：render_slides、montage、detect_font、slides_test；修复非预期重叠、越界后交付。特别注意 [slides_test.py](https://raw.githubusercontent.com/openai/skills/e6afb0d74cc75d220df2faf3dd6c635c2dc6a108/skills/.curated/slides/scripts/slides_test.py) 是扩画布、加灰色边带、渲染后检查越出画布的内容；它不是全能文本框内部溢出检查，更不保证内容正确。

模板约束：参考 deck 先渲染、保持原尺寸和编辑性，但没有强制品牌模板/固定槽位模型。维护信号：官方历史实现可复现获取，main 已移除。适合作为冻结依赖，不适合无条件跟随最新版。

## 3. JetBrains/skills/slides：可获取迁移版，不能当官方 OpenAI 当前发布

一手材料：[SKILL.md](https://github.com/JetBrains/skills/blob/main/slides/SKILL.md)、[文件级许可证](https://raw.githubusercontent.com/JetBrains/skills/main/slides/LICENSE.txt)。frontmatter 的 author 为 OpenAI，source 明确指向上述固定提交；文件级许可证确为 Apache-2.0。

实现差异：同样要求 JS＋PPTX、render、montage、slides_test、detect_font；当前 SKILL.md 不再要求复制 OpenAI helper 目录，也不再指定 autoFontSize 等函数，改为显式安排尺寸和图像裁切。因此不是“OpenAI helper 的原封镜像”，也不是新的自动设计引擎。模板约束和验收偏几何/字体，依然需要独立内容检查。[当前提示词](https://raw.githubusercontent.com/JetBrains/skills/main/slides/SKILL.md)

维护信号：当前 main 文件和四个工具名称可核查；未实测工具，也未断言全目录与上游逐字相同。可作为移植候选，选定后仍应固定 SHA、核对具体脚本与依赖。它与 OpenAI 历史版本有同源关系，不应在质量排行榜里算两项互相独立的证据。

## 4. MiniMax pptx-generator：每页模块和主题合同清晰，验收主要靠提示词

一手材料：[SKILL.md](https://raw.githubusercontent.com/MiniMax-AI/skills/main/skills/pptx-generator/SKILL.md)、[references/pitfalls.md](https://raw.githubusercontent.com/MiniMax-AI/skills/main/skills/pptx-generator/references/pitfalls.md)、[MIT LICENSE](https://raw.githubusercontent.com/MiniMax-AI/skills/main/LICENSE)。

实现：每页生成独立 `slide-XX.js`，同步导出 `createSlide(pres, theme)`；主题仅五个固定键；由 agent 写 `compile.js` 汇总。**compile.js 是 SKILL.md 的代码示例，不是仓库已附带的独立脚本**；[目录](https://github.com/MiniMax-AI/skills/tree/main/skills/pptx-generator)只有 SKILL.md 与 references。默认 10×5.625 英寸，中文微软雅黑、英文 Arial；五类页型、四类样式配方，并有固定页码位置。适合多页任务统一接口，但原规则较刚性，改变画布后页码坐标也要修改。

验收：MarkItDown 提取文本、检查占位词、复核受影响页，要求至少一次修复复核循环；没有证据证明它附带自动几何验收器。文本提取看不出裁切/遮盖；其长标题建议 `fit:'shrink'` 与 OpenAI“不靠 fit/autoFit 做最终排版”的规则不同，不能混用而不测试。[QA 文件](https://github.com/MiniMax-AI/skills/blob/main/skills/pptx-generator/references/pitfalls.md)

维护信号：[目录提交历史](https://github.com/MiniMax-AI/skills/commits/main/skills/pptx-generator)可见 2026-03-21 整理 references；缓存可能不含后续历史。仓库声明 MIT 是明确证据；未完成跨项目文本来源审计，不能仅因相似设计用语就宣称其所有内容无来源风险。

## 5. Frontend Slides：先真实风格预览，再锁定设计系统

一手材料：[实际 plugin skill](https://github.com/zarazhangrui/frontend-slides/blob/main/plugins/frontend-slides/skills/frontend-slides/SKILL.md)、[MIT LICENSE](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/LICENSE)。原项目路径为 **zarazhangrui/frontend-slides**，不是搜索结果中众多同名 fork。

实现：agent 生成单文件 HTML/CSS/JS；先问演讲目的、长度、现有内容、阅读密度，再做三个真实封面预览。预览选项来自 preset、bold template 和自定义方向；用户选定后只加载所选 `design.md`，字体、配色、间距、组件语法贯穿全 deck。固定 1920×1080 舞台同比缩放；必须包含 viewport-base.css。验收特别要求浏览器截图同时检查溢出和面板遮盖，不能仅查 scrollHeight。[设计合同正文](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/plugins/frontend-slides/skills/frontend-slides/SKILL.md)

转换：`extract-pptx.py` 抽内容，再重新设计 HTML；不等同于忠实还原 PPTX 母版。网页内可编辑文本不等于可编辑 PowerPoint。PDF 出口 [export-pdf.sh](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/plugins/frontend-slides/skills/frontend-slides/scripts/export-pdf.sh) 确实使用 Playwright 逐页截图、再将图片放入 PDF，PDF 文字也因此不是原生文字。

维护信号：[提交历史](https://github.com/zarazhangrui/frontend-slides/commits/main)可见 2026 年的密度流程、模板包、非 Claude agent 兼容、导航/编辑导出修复。弱点：提示词要求在线字体；离线可用不能只凭“single-file”判定，需检查字体和素材是否一并本地化。Windows 运行 Bash 出口也需适配，未实测。

## 6. Marp：稳定 Markdown 主题路线，实验可编辑出口经过 PDF 导入

一手材料：[官方站](https://marp.app/)、[CLI README](https://raw.githubusercontent.com/marp-team/marp-cli/main/README.md)、[converter.ts](https://raw.githubusercontent.com/marp-team/marp-cli/main/src/converter.ts)。Marp 不是 agent skill；它是可被 skill 调用的确定性引擎。Markdown 的 `---` 分页、frontmatter/directives 和 CSS theme 是主要合同；可锁定品牌 CSS，限制页型和篇幅，再由 agent 填内容。

实际输出：HTML/PDF；默认 `--pptx` 把渲染页作为整页背景图片，支持讲者 notes。额外 `--pptx --pptx-editable` 明确标实验：需要浏览器与 LibreOffice；复杂主题可能失败/不完整，notes 不支持，官方提示保真下降。[README 导出段](https://github.com/marp-team/marp-cli#experimental-generate-editable-pptx---pptx-editable)

源码证实实验路线是临时 PDF 经 LibreOffice `impress_pdf_import` 转 PPTX，并检查输出文件存在；不是语义层直接生成原生图表。生成能打开的 PPTX 不等于图表数据可编辑。缺少 agent 式逐页内容纠错，需要自行包上 QA。[转换实现](https://raw.githubusercontent.com/marp-team/marp-cli/main/src/converter.ts)

维护与许可：[release 页](https://github.com/marp-team/marp-cli/releases)本次显示 v4.5.1 和后续维护记录；官方工具 MIT，[LICENSE](https://github.com/marp-team/marp-cli/blob/main/LICENSE)。适合纳入低成本基线，实验 editable 单独打分，不能代替原生 PPTX 主线。

## 7. Slidev：可编辑 PPTX 已进入 release，但复杂元素及页面可能回退

一手材料：[官方 exporting](https://sli.dev/guide/exporting)、[v52.20.0 发布](https://github.com/slidevjs/slidev/releases/tag/v52.20.0)、[已合并 PR #2722](https://github.com/slidevjs/slidev/pull/2722)、[MIT LICENSE](https://raw.githubusercontent.com/slidevjs/slidev/main/LICENSE)。PR 于 2026-09-16 合并，release 明确列原生文本/形状导出特性；不是未落地设想。当前 docs 显示 v53.0.0。

普通 `slidev export --format pptx` 仍为整页图，notes 可保留。新 `--format pptx-editable` 在浏览器测量 DOM，再重建文本框和原生形状；SVG/Mermaid、canvas、iframe、视频、公式以及复杂 CSS 等按元素图片化；无法可靠重建的页回退整图并报告。字体不嵌入、长文字换行可能变、某些伪元素装饰被省略；不是完全可编辑保真复制。[官方边界](https://sli.dev/guide/exporting#editable-pptx)

实现可核查 [build.ts](https://raw.githubusercontent.com/slidevjs/slidev/main/packages/slidev/node/commands/pptx/build.ts)：PptxGenJS 写出形状、图片及文字。PR 描述 walker/normalize/capture/build 分层和 OOXML fixture 测试；这些是项目测试证据，不是本研究已跑测试。无 `.potx` 导入、母版合成或字体嵌入承诺。主题/Vue 组件/Markdown 是网页设计合同，PPTX 转换是附加路径。

建议：技术演讲优先 HTML；若需要交 PPTX，同时保留网页参考和 source，抽查所有中文段落、公式、notes、click 步数；记录每页 raster fallback。Slidev 比 Marp 的新转换更接近 DOM 到原生元素，但仍不能未经实测称为“任意网页转完全可编辑 PPT”。

## 可执行试验方案（待总方案审核后运行）

以下是本研究提出的实验合同，不是上游已有保证，也没有开始安装或执行。

1. **冻结候选。** 原生线选 OpenAI 固定提交或 JetBrains 固定 SHA 二选一，避免同源重复计分；MiniMax 仅引入页模块组织。网页线各固定 Frontend Slides、Marp CLI、Slidev 版本；保存许可证/来源清单，禁用自动 @latest。
2. **共同输入。** 用同一份 8 页中文简报：封面、长标题/双列、含来源数字、原生柱线图、流程图、图片注释、对比表、结论；指定 16:9、同一字体与色板。另用合法自有 PPTX 测模板保持。
3. **共同设计合同。** 每页一个结论、证据和来源；字号下限和最多文字量；页型轮换；允许遮盖必须登记；数字不能由 agent 自造。未批准风格前只做 3 个真实封面样稿，选定后锁定合同。
4. **输出全套。** 原生线交 PPTX＋JS＋素材＋PNG；网页线交 HTML/Markdown＋素材＋PDF；Marp/Slidev 分别同时交图片 PPTX 与 editable PPTX，不把两者合并成一个“PPTX 能力”分数。
5. **四道验收。** 内容提取对照输入、全页截图目视、字体/边界/遮盖检查、真实编辑检查；后者必须在 PowerPoint 中改文字和图表、存回并重开，不能只数 ZIP 内的 text runs。统计原生文本比例、原生图表数、图片页数、回退页数与修复次数。
6. **判定。** 审美和编辑性分别评分。原生 PPTX 作为交付主线需所有正文可改、普通数据图表可改数据、零未登记裁切/遮盖；网页用于 HTML 交付时允许图形网页化。任何图片 PPTX 均明确标“演示版”。转换出来的分散矢量线条不算可编辑语义图表。

## 未验证与证据边界

- 未装依赖/执行外部脚本，未测 Windows、LibreOffice 和真实 PowerPoint 的渲染一致性；不能用此文断言运行成本或平均成功率。
- 除 OpenAI 历史 SHA 与 Slidev 发布版本外，其余 main 会变化。正式实验必须保存实际 SHA 和文件哈希。
- GitHub 带缓存的 commit 页面只能作“存在维护记录”的信号，不能证明截止当日最后活跃时间；未使用星数作为质量证据。
- OpenAI helper 索引和 slides_test 源码已读；完整 helper 各算法、JetBrains 全目录差异及依赖许可尚未逐文件审计。
- Slidev capture.ts 与固定 tag 的部分 raw 路径本次抓取失败；build.ts main、合并 PR、官方文档和 release 相互支持功能判断。未把失败路径当作代码不存在。
- 未做 MiniMax 文本溯源审计；“项目声明 MIT”与“第三方来源全部审计完成”是两件事。
- Frontend Slides 的图片 PDF 与 Marp/Slidev 的默认图片 PPTX 均保留外观，但不满足文本/图表原生编辑要求；新可编辑模式的实际保真和回退频率需实验决定。
