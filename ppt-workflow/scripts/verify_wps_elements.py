"""Create and reopen a native WPS element demonstration on owned documents only."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.render import powerpoint_lock, save, sha256


def rgb(value):
    return int(value[:2], 16) + 256 * int(value[2:4], 16) + 65536 * int(value[4:], 16)


def activate():
    import pythoncom
    import win32com.client
    try:
        return win32com.client.GetActiveObject("KWPP.Application")
    except pythoncom.com_error:
        return win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}", clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)


def text(slide, name, value, x, y, w, h, size=18, color="162E3B", bold=False):
    shape = slide.Shapes.AddTextbox(1, x, y, w, h)
    shape.Name = name
    shape.TextFrame.MarginLeft = 0
    shape.TextFrame.MarginRight = 0
    shape.TextFrame.MarginTop = 0
    shape.TextFrame.MarginBottom = 0
    tr = shape.TextFrame.TextRange
    tr.Text = value
    tr.Font.Name = "Microsoft YaHei"
    tr.Font.Size = size
    tr.Font.Color.RGB = rgb(color)
    tr.Font.Bold = bold
    return shape


def shape(slide, name, kind, x, y, w, h, color):
    item = slide.Shapes.AddShape(kind, x, y, w, h)
    item.Name = name
    item.Fill.ForeColor.RGB = rgb(color)
    item.Line.Visible = False
    return item


def page(pres, title, subtitle):
    slide = pres.Slides.Add(pres.Slides.Count + 1, 12)
    slide.FollowMasterBackground = False
    slide.Background.Fill.Solid()
    slide.Background.Fill.ForeColor.RGB = rgb("F5F3ED")
    shape(slide, "accent-rule", 1, 58, 40, 44, 5, "117A7E")
    text(slide, "page-title", title, 58, 61, 844, 51, 29, bold=True)
    text(slide, "page-subtitle", subtitle, 58, 118, 844, 30, 15, "536876")
    text(slide, "footer", "WPS 原生元素测试 · 独立文稿 · 非业务结论", 58, 507, 844, 22, 11, "536876")
    return slide


def create(out, report, owned):
    app = activate()
    report["initial_presentation_count"] = int(app.Presentations.Count)
    pres = app.Presentations.Add(False)
    owned.append(pres)
    pres.PageSetup.SlideWidth = 960
    pres.PageSetup.SlideHeight = 540
    for i in range(pres.Slides.Count, 0, -1):
        pres.Slides.Item(i).Delete()
    slide = page(pres, "用 WPS 原生元素，构建可复用模块", "创建一组卡片，再复制、改字和重排；每个子对象保留独立编辑能力。")
    shape(slide, "card-bg", 5, 58, 177, 260, 237, "FFFFFF")
    shape(slide, "card-mark", 9, 80, 198, 36, 36, "117A7E")
    text(slide, "card-number", "01", 82, 202, 34, 28, 16, "FFFFFF", True).TextFrame.TextRange.ParagraphFormat.Alignment = 2
    text(slide, "card-title", "创建原生形状", 80, 258, 216, 40, 23, bold=True)
    text(slide, "card-body", "圆角矩形、圆形与文字框\r组合成一个设计模块。", 80, 316, 216, 65, 17, "536876")
    names = ("card-bg", "card-mark", "card-number", "card-title", "card-body")
    group = slide.Shapes.Range(names).Group()
    group.Name = "native-card-original"
    for i, (title, body) in enumerate([
        ("复制并修改内容", "复制现有模块，替换文案，\r保持颜色与字号一致。"),
        ("复用组合模块", "整组移动或缩放，\r也能单独修改内部元素。")], 1):
        # This WPS version's Shape.Duplicate returned a handle but omitted
        # the duplicate from the saved slide. Use the native copy/paste route.
        group.Copy()
        duplicate = slide.Shapes.Paste().Item(1)
        duplicate.Name = f"native-card-copy-{i}"
        duplicate.Left = 58 + i * 292
        duplicate.Top = 177
        duplicate.GroupItems.Item("card-title").TextFrame.TextRange.Text = title
        duplicate.GroupItems.Item("card-body").TextFrame.TextRange.Text = body
        duplicate.GroupItems.Item("card-number").TextFrame.TextRange.Text = f"0{i + 1}"
    report["checks"]["shapes_text_group_duplicate"] = "passed"
    slide = page(pres, "连接线与表格，也是原生对象", "流程使用连接符连接节点；表格直接由 WPS 创建并填写单元格。")
    nodes = []
    for i, label in enumerate(["明确需求", "适配内容", "审核交付"]):
        node = shape(slide, f"flow-node-{i + 1}", 5, 58 + i * 322, 182, 200, 72, "117A7E")
        node.TextFrame.TextRange.Text = label
        node.TextFrame.TextRange.Font.Name = "Microsoft YaHei"
        node.TextFrame.TextRange.Font.Size = 23
        node.TextFrame.TextRange.Font.Color.RGB = rgb("FFFFFF")
        nodes.append(node)
    for i in range(2):
        connector = slide.Shapes.AddConnector(1, 258 + i * 322, 218, 380 + i * 322, 218)
        connector.Name = f"native-connector-{i + 1}"
        connector.ConnectorFormat.BeginConnect(nodes[i], 4)
        connector.ConnectorFormat.EndConnect(nodes[i + 1], 2)
        connector.Line.ForeColor.RGB = rgb("117A7E")
        connector.Line.Weight = 2
        connector.Line.EndArrowheadStyle = 3
    table = slide.Shapes.AddTable(4, 3, 58, 310, 844, 160)
    table.Name = "native-table"
    data = [["元素", "测试动作", "保留形式"], ["组合模块", "创建、复制、修改子对象", "形状与文字"],
            ["流程连接符", "创建并连接两端节点", "连接线"], ["表格", "创建并改写单元格", "原生单元格"]]
    for i, row in enumerate(data, 1):
        for j, value in enumerate(row, 1):
            cell = table.Table.Cell(i, j).Shape
            cell.TextFrame.TextRange.Text = value
            cell.TextFrame.TextRange.Font.Name = "Microsoft YaHei"
            cell.TextFrame.TextRange.Font.Size = 16
            cell.TextFrame.TextRange.Font.Color.RGB = rgb("FFFFFF" if i == 1 else "162E3B")
            cell.Fill.ForeColor.RGB = rgb("117A7E" if i == 1 else "E2EFEB")
    table.Table.Cell(4, 2).Shape.TextFrame.TextRange.Text = "保存前再次修改单元格"
    report["checks"]["connectors_create_attach"] = "passed"
    report["checks"]["table_create_edit"] = "passed"
    slide = page(pres, "图表能力，要区分创建与模板复用", "已有模板的原生图表已验证；本页单独探测当前 WPS 的直接创建接口。")
    try:
        chart_shape = slide.Shapes.AddChart(51, 58, 173, 610, 300)
        chart_shape.Name = "native-chart"
        chart_shape.Chart.ChartStyle = 10
        report["checks"]["chart_create_style"] = "passed"
        report["chart_series_count"] = int(chart_shape.Chart.SeriesCollection().Count)
        text(slide, "chart-note", "图表由 WPS 创建\r样式可继续修改\r数据可单独检查", 708, 230, 202, 135, 19, "117A7E")
    except Exception as exc:
        report["checks"]["chart_create_style"] = "unverified"
        report["chart_error"] = str(exc)
        source = ROOT / "templates/imported/WPS-Green-Report.pptx"
        try:
            report["chart_source_sha256"] = sha256(source)
            snapshot = out / "chart-source.pptx"
            shutil.copyfile(source, snapshot)
            source_pres = app.Presentations.Open(str(snapshot), False, True, False)
            owned.append(source_pres)
            shapes = source_pres.Slides.Item(9).Shapes
            original_chart = next(shapes.Item(i) for i in range(1, shapes.Count + 1) if shapes.Item(i).Id == 7)
            original_chart.Copy()
            copied_chart = slide.Shapes.Paste().Item(1)
            copied_chart.Name = "template-native-chart"
            copied_chart.Left, copied_chart.Top = 58, 174
            copied_chart.Width, copied_chart.Height = 600, 292
            assert copied_chart.HasChart
            copied_chart.Chart.ChartStyle = 10
            report["checks"]["template_chart_copy_style"] = "passed"
            source_pres.Close()
            owned.remove(source_pres)
            assert sha256(source) == report["chart_source_sha256"]
            text(slide, "chart-note", "模板图表：复制成功\r仍是原生图表对象\r\r直接创建接口未通过\r可优先复用已有图表", 702, 215, 206, 210, 18, "117A7E")
        except Exception as copy_error:
            report["checks"]["template_chart_copy_style"] = "unverified"
            report["chart_copy_error"] = str(copy_error)
            text(slide, "chart-note", "当前图表接口未通过\r详情见测试报告", 58, 200, 844, 100, 23, "117A7E")
    try:
        layouts = app.SmartArtLayouts
        report["smartart_layouts_count"] = int(layouts.Count)
        if layouts.Count:
            probe = page(pres, "直接使用 WPS 内置 SmartArt 图示", "当前安装提供的布局库；创建后修改节点，保存后再核对是否仍可编辑。")
            chosen = layouts.Item(1)
            for i in range(1, layouts.Count + 1):
                candidate = layouts.Item(i)
                if candidate.Name in ("基本流程", "Basic Process", "基本块列表"):
                    chosen = candidate
                    break
            art = probe.Shapes.AddSmartArt(chosen, 58, 174, 844, 296)
            art.Name = "native-smartart"
            report["checks"]["smartart_create"] = "passed" if art is not None else "unverified"
            report["smartart_layout_name"] = str(chosen.Name)
            labels = ["明确需求", "整理资料", "选择模板", "制作内容", "审核交付"]
            nodes = art.SmartArt.AllNodes
            report["smartart_node_count"] = int(nodes.Count)
            report["smartart_text"] = []
            for i in range(1, nodes.Count + 1):
                value = labels[(i - 1) % len(labels)]
                nodes.Item(i).TextFrame2.TextRange.Text = value
                nodes.Item(i).TextFrame2.TextRange.Font.Name = "Microsoft YaHei"
                nodes.Item(i).TextFrame2.TextRange.Font.Size = 22
                report["smartart_text"].append(value)
            report["checks"]["smartart_node_edit"] = "passed"
            try:
                art.SmartArt.Color = app.SmartArtColors.Item(4)
                report["checks"]["smartart_colors"] = "passed"
            except Exception as exc:
                report["smartart_style_error"] = str(exc)
        else:
            report["checks"]["smartart_create"] = "unavailable"
    except Exception as exc:
        report["checks"]["smartart_create"] = "unverified"
        report["smartart_error"] = str(exc)
        report["smartart_traceback"] = traceback.format_exc()
        if pres.Slides.Count > 3:
            pres.Slides.Item(4).Delete()
    output = out / "wps-native-elements.pptx"
    pres.SaveAs(str(output), 24)
    (out / "slides").mkdir()
    for i in range(1, pres.Slides.Count + 1):
        pres.Slides.Item(i).Export(str(out / "slides" / f"slide-{i}.png"), "PNG", 1600, 900)
    report.update(status="created", deck=str(output), output_sha256=sha256(output), slide_count=int(pres.Slides.Count))


def readback(out, report, owned):
    app = activate()
    pres = app.Presentations.Open(str(out / "wps-native-elements.pptx"), True, False, False)
    owned.append(pres)
    first = pres.Slides.Item(1)
    original = first.Shapes.Item("native-card-original")
    copied = first.Shapes.Item("native-card-copy-1")
    assert original.GroupItems.Count == copied.GroupItems.Count == 5
    assert original.GroupItems.Item("card-title").TextFrame.TextRange.Text == "创建原生形状"
    assert copied.GroupItems.Item("card-title").TextFrame.TextRange.Text == "复制并修改内容"
    second = pres.Slides.Item(2)
    assert second.Shapes.Item("native-table").Table.Cell(4, 2).Shape.TextFrame.TextRange.Text == "保存前再次修改单元格"
    for i in range(1, 3):
        c = second.Shapes.Item(f"native-connector-{i}").ConnectorFormat
        assert c.BeginConnected and c.EndConnected
    created = json.loads((out / "created.json").read_text(encoding="utf-8"))
    if created["checks"].get("chart_create_style") == "passed":
        assert pres.Slides.Item(3).Shapes.Item("native-chart").HasChart
    if created["checks"].get("template_chart_copy_style") == "passed":
        assert pres.Slides.Item(3).Shapes.Item("template-native-chart").HasChart
        report["template_chart_copy_preserved"] = True
    if created["checks"].get("smartart_node_edit") == "passed":
        art = pres.Slides.Item(4).Shapes.Item("native-smartart")
        actual = [art.SmartArt.AllNodes.Item(i).TextFrame2.TextRange.Text for i in range(1, art.SmartArt.AllNodes.Count + 1)]
        assert actual == created["smartart_text"]
        report["smartart_nodes_preserved"] = actual
    report.update(status="completed", slide_count=int(pres.Slides.Count), native_readback="passed",
                  group_children=5, duplicate_does_not_change_source=True, table_edit_preserved=True,
                  connector_endpoints_preserved=True)


def worker(out, mode):
    import pythoncom
    report = dict(status="failed", checks={}, application_quit_called=False)
    owned = []
    pythoncom.CoInitialize()
    try:
        (create if mode == "create" else readback)(out, report, owned)
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        for pres in reversed(owned):
            try:
                pres.Close()
            except Exception as exc:
                report["cleanup_error"] = str(exc)
        owned.clear()
        gc.collect()
        pythoncom.CoUninitialize()
        report["cleanupCompleted"] = "cleanup_error" not in report
        save(out / ("created.json" if mode == "create" else "readback.json"), report)
    return 0 if report["status"] in {"created", "completed"} and report["cleanupCompleted"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["create", "readback"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    out = args.output.resolve()
    if out == ROOT / "runs" or not out.is_relative_to(ROOT / "runs"):
        parser.error("Fresh output subdirectory inside runs required")
    if args.mode:
        return worker(out, args.mode)
    out.mkdir(parents=True, exist_ok=False)
    with powerpoint_lock(ROOT / "runs/.powerpoint-worker-lock") as lock:
        try:
            for mode, timeout in [("create", 40), ("readback", 20)]:
                p = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(out), "--mode", mode],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                r = json.loads((out / ("created.json" if mode == "create" else "readback.json")).read_text(encoding="utf-8"))
                if not r.get("cleanupCompleted"):
                    save(lock / "quarantine.json", dict(reason="WPS owned element-test cleanup uncertain", output=str(out)))
                if p.returncode:
                    print(json.dumps(r, ensure_ascii=True))
                    return 1
            print(json.dumps(dict(create=json.loads((out / "created.json").read_text(encoding="utf-8")), readback=r), ensure_ascii=True))
            return 0
        except subprocess.TimeoutExpired:
            save(lock / "quarantine.json", dict(reason="WPS native element test timeout; shared app retained", output=str(out)))
            raise


if __name__ == "__main__":
    raise SystemExit(main())
