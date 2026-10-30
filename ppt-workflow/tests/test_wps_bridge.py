import json
from pathlib import Path
import tempfile
import unittest
from ppt_workflow.wps_bridge import ROOT, validate_request


class WPSRequestTests(unittest.TestCase):
    def setup_request(self, directory, **updates):
        data = dict(template_path=str(ROOT / "templates/unified-v3/Unified-Ivory.potx"), pages=[1, 2], edits=[])
        data.update(updates)
        request = Path(directory) / "request.json"
        request.write_text(json.dumps(data), encoding="utf-8")
        return request

    def test_valid_request_freezes_source_without_creating_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            output, data = validate_request(self.setup_request(temp), Path(temp) / "out")
            self.assertEqual(len(data["source_sha256"]), 64)
            self.assertFalse(output.exists())

    def test_existing_or_external_output_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            request = self.setup_request(temp)
            for output in (Path(temp), ROOT.parent / "wps-outside-test"):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    validate_request(request, output)

    def test_page_order_duplicates_and_unknown_fields_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            for changes in (dict(pages=[2, 1]), dict(pages=[1, 1]), dict(pages=[True]), dict(pages=[]), dict(arbitrary_script="bad")):
                request = self.setup_request(temp, **changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    validate_request(request, Path(temp) / "out")

    def test_duplicate_or_invalid_text_edits_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as temp:
            edit = dict(slide=1, shape_id=16, expected="old", text="new")
            for edits in ([edit, edit], [dict(edit, slide=3)], [dict(edit, text="x" * 2001)], [dict(edit, command="bad")]):
                request = self.setup_request(temp, edits=edits)
                with self.subTest(edits=edits), self.assertRaises(ValueError):
                    validate_request(request, Path(temp) / "out")
