"""Write the human review packet only after recorded P2 evidence is present."""
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import sha256,save
STAGE=ROOT.parent/"06-实施与阶段审核/P2"
verification=json.loads((STAGE/"verification.json").read_text(encoding="utf-8"))
assert verification["tests"]==dict(run=112,failures=0,errors=0,skipped=0)
assert all(x["unchanged"] for x in verification["originals"])
assert all(s["render"]=="passed" and not s["issues"] for s in verification["samples"])
for s in verification["samples"]:assert sha256(s["path"])==s["sha256"]
report=f'''# P2 阶段审核：内容、主题与可编辑组件

日期：2026-10-14。实施已完成，停在 G2，等待用户审核。P1 已根据用户“继续”指令记为通过。P3 尚未开始。

## 需要审核的成品

三套主题共用相同的十页材料与版式，以比较阅读效果。样例讨论“教学报告自动化试点”，所有耗时都是明确披露的示意设定，不代表真实项目实测。

| 主题 | PPTX | 十页接触表 | 代表页 |
|---|---|---|---|
| 学术 | [打开学术样例]({(STAGE/'样例/academic/deck.pptx').as_posix()}) | [查看接触表]({(STAGE/'样例/academic/contact.png').as_posix()}) | [图表]({(STAGE/'样例/academic/slides/slide-005.png').as_posix()})、[表格]({(STAGE/'样例/academic/slides/slide-008.png').as_posix()}) |
| 商务 | [打开商务样例]({(STAGE/'样例/business/deck.pptx').as_posix()}) | [查看接触表]({(STAGE/'样例/business/contact.png').as_posix()}) | [图表]({(STAGE/'样例/business/slides/slide-005.png').as_posix()})、[表格]({(STAGE/'样例/business/slides/slide-008.png').as_posix()}) |
| 技术 | [打开技术样例]({(STAGE/'样例/technical/deck.pptx').as_posix()}) | [查看接触表]({(STAGE/'样例/technical/contact.png').as_posix()}) | [图表]({(STAGE/'样例/technical/slides/slide-005.png').as_posix()})、[表格]({(STAGE/'样例/technical/slides/slide-008.png').as_posix()}) |

请重点审核三点：主题风格是否合适、展示时的阅读尺度是否足够、内容密度与信息顺序是否需要调整。接触表便于看整体节奏，详细字形和表格内容请看全尺寸 PNG 或 PPTX。

## 实际实现

1. **来源与事实记录**：source ID、原文 JSON Pointer、数值、单位、统计口径、时间、示意标志、指标键和显式公式。重复指标按口径与时间核对。示意源与事实逐字段比对。
2. **跨页绑定**：正文通过事实文本模板展开，图表数据点与表格事实单元格引用相同事实 ID。修改某页显示值或图表单位会被检测。中文“数字＋分钟/秒/倍”的未绑定说法报错。
3. **统一示例**：人工汇总 40 分钟、自动汇总 1 分钟、节省 39 分钟、耗时比 40 倍，全部不含人工审核。新示例没有无解释的 0.9 秒口径。历史示例原件没有改动。
4. **三套主题、十类参数化版式**：封面、结论、KPI、对比、图表＋结论、流程、时间线、表格、章节、结尾请求。主题色和字体可覆盖。版式与业务示例内容分离，超出初期行列/项目数量时明确拒绝，不丢项。
5. **原生输出与映射**：每套 101 个元素均映射到实际输出对象。图表保留内嵌 XLSX，表格保留单元格，流程保留形状、文本与连接线。逻辑 group ID 留在 spec/map 中，本阶段没有承诺 PowerPoint 物理组合。
6. **局部图片登记**：登记源 ID、许可说明、文件 hash 与像素尺寸，检查构建前文件与输出图片字节一致性。成品样例没有栅格对象；图片通路用独立测试验收。
7. **可审计的导出修正**：PptxGenJS 4.0.1 的多余母版声明与二维图表系列轴引用由受限规则处理。每套记录十项修正，保留 raw 输出和 hash。不修改图文或数据，不掩盖未知轴错误。

实现位置：`ppt-workflow/ppt_workflow/design.py`、`content.py`、`assets.py`、`export_fix.py` 与 `engine/build.cjs`。自有坐标计算不访问 PptxGenJS 私有 `_slideObjects`。本轮没有新增第三方依赖。

## 验证证据

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 全部回归 | 112 项通过，0 失败，0 跳过 | tests.json / tests.log |
| P2 新增测试 | 37 项，覆盖事实冲突、公式、跨页漂移、来源、绑定、原生对象/工作簿篡改、受限修正、素材登记 | tests/test_p2.py |
| 合同兼容性 | 原有 18 项合同测试仍通过 | tests.json |
| 原文件保护 | 54 个历史文件 hash 全部不变 | verification.json |
| 三套静态检查 | 每套 0 错误、0 警告；几何与内容已通过 | 样例各主题 qa.json |
| 原生图表与表格 | 类别、系列名、数值缓存、工作簿引用及单元格与 spec 一致 | object-map.json / inspection-details.json |
| 实际渲染 | PowerPoint 16.0，build 20430，三套各10页，合计30张1600×900 PNG | 各主题 render-manifest.json |
| 实际文本边界 | 每套78个普通文本框有 Office 计算边界，没有确认的溢出 | inspection-details.json / target_bounds |
| 实际编辑探针 | 学术主题副本：图表缩窄0.25英寸、修改表格单元格和标题，保存并重开成功；内嵌图表数据保留，原件 hash 不变 | edit-probe.json |
| 宿主图像审阅 | 三套十页接触表逐页查看，图表和表格共6张全尺寸 PNG 复核，无发现阻断问题 | visual-review.json |

审核副本与 run 中的成品 hash 一致。代码、合同、测试、来源示例和渲染 worker 的阶段快照保存在 `code-snapshot/`，用于后续变更追踪。早期草稿保留在 `ppt-workflow/runs/p2-draft-*` 和 `p2-review-001`，本次审核以 `样例/` 中的副本为准。

## 限制与待验证项

总体 QA 仍为 **unverified**。这不是渲染失败：完整 OOXML Schema 未运行，字体测量仍有估算成分，表格继承和图表标签几何尚未全部建模。实际 PNG 已单独审阅，未知项没有被删掉或当成自动检查通过。

完整 Office 图像验收覆盖本例横向条形图；柱形、折线、饼图分支尚未逐种真实验收，散点图拒绝构建。工作簿核对支持单个单元格或单列范围，多层类别缓存不支持。编辑探针只针对学术主题的代表对象，商务/技术主题仅完成原生结构、数据与渲染检查；没有逐种验证图表数据编辑及全部对象操作。LibreOffice、Google Slides 未验证。

来源实质核对当前支持明确的本地 JSON 示意记录。外部网页、PDF 引文能否支持业务结论仍需研究和人工审核。三套主题是共享版式的颜色/对比度系统，尚未用真实品牌模板验收。当前版式有明确项目数量限制，长内容需要修订或自定义 scene，自动分页在范围之外。

## 可运行命令

从 `ppt-workflow/` 目录执行，使用全新输出目录：

```powershell
& .venv/Scripts/python.exe scripts/build_p2.py --out runs/p2-rebuild-new
& .venv/Scripts/python.exe scripts/render_p2.py runs/p2-rebuild-new
& .venv/Scripts/python.exe scripts/bind_p2_render.py runs/p2-rebuild-new
& .venv/Scripts/python.exe -m unittest discover -s tests -v
```

主题与版式参数详见 [组件接口]({(STAGE/'组件接口.md').as_posix()})。Office 检查必须使用没有用户 PowerPoint 会话的独立工作进程；超时与清理不确定时保留隔离锁。

## G2 审核与下一步

请给出“通过”“带条件通过”或具体修改意见。若回复“继续”，按已约定的阶段审核方式记为允许进入 P3。

P3 范围：正式 CLI、任务状态与 revision、输入/审核 hash 绑定、有限修复、断点续跑、交付门、故障演示及新的自有 Skill。未验证项必须在覆盖声明和交付门中明确处理，不能仅因本次渲染成功就直接变成通过。真实模板和其他开源通路比较仍留在 P4。
'''
(STAGE/"P2阶段审核.md").write_text(report,encoding="utf-8")
visual='''# P2 宿主图像审阅记录

审阅对象：p2-review-002 的三个主题，对应审核包“样例”副本。详细输入和图片 hash 见 visual-review.json。

查看了三套十页接触表，以及三套第5页图表、第8页表格的1600×900原图。各页标题、正文、来源说明完整。没有看到溢出、截断或非预期相互遮挡。图表零起点、类别标签、1与40的数据标签一致，39分钟侧注明确不含审核。表格四行数据与叙述口径一致，深色主题表头和正文对比清楚。流程连接线与四步顺序相符。

第一轮审阅发现表格页有“事实 ID”实现术语、结尾“期末”与四周试点的表述不够一致。本阶段已分别改为“各页沿用相同口径”和“试点结束”，新副本已经重新导出并审阅。该记录是 Codex 的宿主图像审阅，不是用户对 G2 的审核批准，也不是所有对象的自动几何测量。
'''
(STAGE/"视觉审核.md").write_text(visual,encoding="utf-8")
state_path=STAGE.parent/"阶段状态.json";state=json.loads(state_path.read_text(encoding="utf-8-sig"))
state["active_stage"]="P2"
state["stages"]["P2"].update(implementation="completed",review="awaiting_user",report="P2/P2阶段审核.md",next_stage_requires_user_approval=True)
save(state_path,state)
# Refresh the snapshot after the collector/finalizer was finalized; no test/source behavior changes here.
files=[]
for base in ["ppt_workflow","schemas","scripts","tests","engine","examples","render"]:
    files.extend(p for p in (ROOT/base).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
files+=[ROOT/"README.md",ROOT/"P2组件说明.md",ROOT/"package.json",ROOT/"package-lock.json",ROOT/"requirements.lock.txt"]
verification["source_hashes"]=[]
for source in files:
    rel=source.relative_to(ROOT);dest=STAGE/"code-snapshot"/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    verification["source_hashes"].append(dict(path=str(rel),sha256=sha256(source)))
verification["review_packet_hashes"]=[dict(path=filename,sha256=sha256(STAGE/filename)) for filename in ["P2阶段审核.md","视觉审核.md","组件接口.md","visual-review.json","tests.json","sources.json"]]
save(STAGE/"verification.json",verification)
print(json.dumps(dict(stage="P2",review="awaiting_user",report=str(STAGE/"P2阶段审核.md"),snapshot_files=len(files)),ensure_ascii=False))
