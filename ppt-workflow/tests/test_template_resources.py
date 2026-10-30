import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches
from ppt_workflow.template_resources import ROOT, inspect_template


class TemplateResourceTests(unittest.TestCase):
    def test_frozen_potx_inventory_preserves_source(self):
        source = ROOT / "templates/unified-v3/Unified-Ivory.potx"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            result = inspect_template(source, Path(temp) / "report")
            report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
            self.assertEqual(result["counts"]["layouts"], 10)
            self.assertEqual(result["counts"]["masters"], 1)
            self.assertIn("Unified 01 Cover", [r["name"] for r in report["layouts"]])
            self.assertFalse(report["external_resources_fetched"])
        self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_pptx_native_chart_and_table_are_identified(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            source = Path(temp) / "native.pptx"
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            chart = CategoryChartData()
            chart.categories = ["A", "B"]
            chart.add_series("Values", [1, 2])
            slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(4), Inches(2), chart)
            slide.shapes.add_table(2, 2, Inches(1), Inches(4), Inches(4), Inches(1))
            prs.save(source)
            result = inspect_template(source, Path(temp) / "report")
            report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
            self.assertEqual(result["counts"]["chart_parts"], 1)
            shapes = report["slides"][0]["shapes"]
            self.assertEqual(sum(s["chart"] for s in shapes), 1)
            self.assertEqual(sum(s["table"] for s in shapes), 1)
            self.assertEqual(len({s["id"] for s in shapes}), len(shapes))

    def test_external_output_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as temp:
            with self.assertRaisesRegex(ValueError, "stay inside"):
                inspect_template(ROOT / "templates/unified-v3/Unified-Ivory.potx", Path(temp) / "out")
            self.assertFalse((Path(temp) / "out").exists())

    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            marker = Path(temp) / "template-resources.json"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Fresh output"):
                inspect_template(ROOT / "templates/unified-v3/Unified-Ivory.potx", temp)
            self.assertEqual(marker.read_text(), "keep")

    def test_invalid_package_and_dps_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            for extension in ("pptx", "dps"):
                source = Path(temp) / ("bad." + extension)
                source.write_text("invalid")
                with self.subTest(extension=extension), self.assertRaises(ValueError):
                    inspect_template(source, Path(temp) / "report")
                self.assertFalse((Path(temp) / "report").exists())
