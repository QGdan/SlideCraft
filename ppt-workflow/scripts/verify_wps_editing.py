"""Test WPS on owned scratch files only; never quit a shared WPS application."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(path):
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333333), Inches(7.5)
    titles = ["WPS 原生模板与编辑验证", "原生图表与表格", "原生流程模块"]
    for index, title in enumerate(titles):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        shape = slide.shapes.add_textbox(Inches(.8), Inches(.8), Inches(11.8), Inches(.9))
        shape.name = "test-title"
        run = shape.text_frame.paragraphs[0].add_run()
        run.text = title
        run.font.name, run.font.size = "Microsoft YaHei", Pt(34)
        run.font.color.rgb = RGBColor.from_string("162E3B")
        note = slide.shapes.add_textbox(Inches(.8), Inches(1.7), Inches(11.5), Inches(.5))
        note.text = "独立测试文稿 · 全部数值为示意数据 · 非业务成品"
        note.text_frame.paragraphs[0].font.size = Pt(16)
    chart = CategoryChartData()
    chart.categories = ["调整前", "调整后"]
    chart.add_series("示意值", [40, 84])
    prs.slides[1].shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(.8), Inches(2.5), Inches(6.8), Inches(3.6), chart).name = "test-chart"
    table = prs.slides[1].shapes.add_table(3, 3, Inches(8), Inches(2.5), Inches(4.5), Inches(2.5)).table
    for i, row in enumerate([["项目", "数值", "说明"], ["调整前", "40", "示意"], ["调整后", "84", "示意"]]):
        for j, value in enumerate(row):
            table.cell(i, j).text = value
    prs.save(path)


def worker(out, template):
    import pythoncom
    import win32com.client
    report = dict(status="failed", operations=[], application_quit_called=False, cleanupCompleted=False)
    app = None
    owned = []
    pythoncom.CoInitialize()
    try:
        app = win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}",
                clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)
        report.update(version=str(app.Version), initial_presentation_count=int(app.Presentations.Count), template_sha256=digest(template))
        pres = app.Presentations.Open(str(template), False, True, False)
        owned.append(pres)
        report["template_layout_count"] = int(pres.SlideMaster.CustomLayouts.Count)
        pres.SaveAs(str(out / "from-template.pptx"), 24)
        pres.Close()
        owned.remove(pres)
        report["operations"].append("POTX-to-independent-PPTX")
        seed(out / "seed.pptx")
        seed_hash = digest(out / "seed.pptx")
        pres = app.Presentations.Open(str(out / "seed.pptx"), False, True, False)
        owned.append(pres)
        pres.ApplyTemplate(str(template))
        report["operations"].append("native-ApplyTemplate")
        for index, layout in [(1, 1), (2, 5), (3, 6)]:
            slide = pres.Slides.Item(index)
            slide.CustomLayout = pres.SlideMaster.CustomLayouts.Item(layout)
            title = slide.Shapes.Item("test-title")
            title.TextFrame.TextRange.Text = ["WPS 模板与可编辑对象验证", "图表数据与表格保存验证", "流程模块：逐个元素可编辑"][index - 1]
            # Empty placeholders inserted by the template are not test content.
            for j in range(slide.Shapes.Count, 0, -1):
                shape = slide.Shapes.Item(j)
                if shape.Type == 14 and shape.HasTextFrame and not shape.TextFrame.HasText:
                    shape.Delete()
        report["operations"].append("native-text-edit")
        slide = pres.Slides.Item(3)
        names = []
        for i, label in enumerate(["选择模板", "对象适配", "审核交付"]):
            shape = slide.Shapes.AddShape(5, 58 + i * 302, 205, 260, 105)
            shape.Name = f"wps-step-{i + 1}"
            names.append(shape.Name)
            shape.Fill.ForeColor.RGB = 0x7E7A11
            shape.Line.Visible = False
            shape.TextFrame.TextRange.Text = label
            shape.TextFrame.TextRange.Font.Name = "Microsoft YaHei"
            shape.TextFrame.TextRange.Font.Size = 24
            shape.TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
        group = slide.Shapes.Range(tuple(names)).Group()
        group.Name = "wps-editable-process"
        report["operations"].append("native-shape-create-and-group")
        chart = pres.Slides.Item(2).Shapes.Item("test-chart").Chart
        chart.ChartStyle = 10
        report["operations"].append("native-chart-style")
        result = out / "wps-edited.pptx"
        pres.SaveAs(str(result), 24)
        images = out / "slides"
        images.mkdir()
        for i in range(1, pres.Slides.Count + 1):
            pres.Slides.Item(i).Export(str(images / f"slide-{i}.png"), "PNG", 1600, 900)
        report["operations"].append("native-PPTX-save-and-PNG-export")
        pres.Close()
        owned.remove(pres)
        pres = app.Presentations.Open(str(result), True, False, False)
        owned.append(pres)
        report["reopened_slide_count"] = int(pres.Slides.Count)
        report["reopened_titles"] = [pres.Slides.Item(i).Shapes.Item("test-title").TextFrame.TextRange.Text for i in range(1, 4)]
        report["reopened_group_size"] = int(pres.Slides.Item(3).Shapes.Item("wps-editable-process").GroupItems.Count)
        report["reopened_chart_has_chart"] = bool(pres.Slides.Item(2).Shapes.Item("test-chart").HasChart)
        report["operations"].append("reopen-and-native-object-readback")
        if digest(template) != report["template_sha256"] or digest(out / "seed.pptx") != seed_hash:
            raise RuntimeError("Original template or seed changed")
        report.update(status="completed", output=str(result), output_sha256=digest(result), inputs_unchanged=True)
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for presentation in reversed(owned):
            try:
                presentation.Close()
            except Exception as exc:
                report["cleanupError"] = str(exc)
        owned.clear()
        app = None
        gc.collect()
        pythoncom.CoUninitialize()
        report["cleanupCompleted"] = "cleanupError" not in report
        (out / "wps-editing.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["status"] == "completed" and report["cleanupCompleted"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    out, template = args.output.resolve(), args.template.resolve()
    if out == ROOT / "runs" or not out.is_relative_to(ROOT / "runs"):
        parser.error("Fresh output subdirectory inside runs required")
    if not template.is_relative_to(ROOT) or not template.is_file() or template.suffix.lower() != ".potx":
        parser.error("Existing project-local POTX required")
    if args.worker:
        return worker(out, template)
    out.mkdir(parents=True, exist_ok=False)
    from ppt_workflow.render import powerpoint_lock
    with powerpoint_lock(ROOT / "runs/.powerpoint-worker-lock") as lock:
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(out), str(template), "--worker"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=55,
                creationflags=subprocess.CREATE_NO_WINDOW)
            (out / "process.json").write_text(json.dumps(dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)), encoding="utf-8")
            report = json.loads((out / "wps-editing.json").read_text(encoding="utf-8"))
            if not report.get("cleanupCompleted"):
                (lock / "quarantine.json").write_text(json.dumps(report), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return result.returncode
        except subprocess.TimeoutExpired:
            (lock / "quarantine.json").write_text(json.dumps(dict(reason="WPS editing timeout; shared app retained", output=str(out))), encoding="utf-8")
            raise


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
