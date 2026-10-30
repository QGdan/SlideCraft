import copy
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from pptx import Presentation
from PIL import Image
from ppt_workflow.editorial import editorial_deck
from ppt_workflow.content import inspect_native,check_ledger
from ppt_workflow.contracts import validate
from ppt_workflow.office_bridge import workspace_path,native_operation
from ppt_workflow.render import sha256

ROOT=Path(__file__).resolve().parents[1]
OFFICE=ROOT/"runs/p2-editorial-office-004"
REUSE=ROOT/"runs/p2-editorial-template-reuse-001"


class EditorialTests(unittest.TestCase):
    def setUp(self):self.spec,_=editorial_deck()
    def test_scene_and_canonical_facts_remain_valid(self):
        self.assertFalse(validate(self.spec,"deck"));self.assertEqual(check_ledger(self.spec,ROOT).status,"passed")
    def test_ten_layouts_preserved(self):self.assertEqual(len({s["layout"] for s in self.spec["slides"]}),10)
    def test_generated_art_is_registered_and_disclosed(self):
        self.assertEqual(len(self.spec["assets"]),3)
        for page in self.spec["slides"]:
            if any(e["type"]=="image" for e in page["elements"]):self.assertTrue(any("AI 生成" in e.get("text","") for e in page["elements"] if e["role"]=="source"))
    def test_review_cutout_has_actual_transparency(self):
        with Image.open(ROOT/"assets/editorial-v2/review.png") as im:self.assertIn("A",im.getbands());self.assertEqual(im.getchannel("A").getextrema()[0],0)
    def test_all_native_and_registered_image_objects_survive_office_save(self):
        r=inspect_native(OFFICE/"deck.pptx",self.spec);self.assertEqual(r.status,"passed",r.issues);self.assertEqual(len(r.details["mapping"]),99)
    def test_template_has_real_template_content_type(self):
        with ZipFile(OFFICE/"Editorial-Teal.potx") as z:self.assertIn(b"presentationml.template.main+xml",z.read("[Content_Types].xml"))
    def test_four_native_master_layouts_and_applied_designs(self):
        record=json.loads((OFFICE/"office-worker.json").read_text(encoding="utf-8"))
        self.assertEqual({x["name"] for x in record["slide_layouts"]},{"Editorial Cover","Editorial Light","Editorial Dark","Editorial Section"})
        native=Presentation(OFFICE/"deck.pptx");names={l.name for l in native.slide_masters[0].slide_layouts}
        self.assertTrue({"Editorial Cover","Editorial Light","Editorial Dark","Editorial Section"}<=names)
    def test_raw_placeholder_is_not_reported_as_native_process(self):
        raw=ROOT/"runs/p2-editorial-002/normalized.pptx"
        self.assertIn("native-diagram-text-mismatch",{i["rule"] for i in inspect_native(raw,self.spec).issues})
    def test_grouped_process_remains_editable_and_ordered(self):
        r=inspect_native(OFFICE/"deck.pptx",self.spec);self.assertEqual(r.details["diagrams"][0]["nodes"],["成绩输入","规则汇总","初稿生成","教师审核"])
        self.assertTrue(r.details["diagrams"][0]["native_group"])
    def test_process_text_tampering_is_detected(self):
        spec=copy.deepcopy(self.spec);next(e for s in spec["slides"] for e in s["elements"] if e["type"]=="diagram")["diagram"]["nodes"][0]="伪造步骤"
        self.assertIn("native-diagram-text-mismatch",{i["rule"] for i in inspect_native(OFFICE/"deck.pptx",spec).issues})
    def test_actual_mcp_result_is_bound_to_office_output(self):
        m=json.loads((OFFICE/"mcp-client.json").read_text(encoding="utf-8"));w=json.loads((OFFICE/"office-worker.json").read_text(encoding="utf-8"))
        self.assertEqual(m["protocol"],"MCP stdio");self.assertFalse(m["result"]["is_error"]);self.assertEqual(w["output_sha256"],sha256(OFFICE/"deck.pptx"))
    def test_template_reuse_preserves_native_chart_data_and_scene(self):
        self.assertEqual(inspect_native(REUSE/"from-template.pptx",self.spec).status,"passed")
        record=json.loads((REUSE/"office-worker.json").read_text(encoding="utf-8"));self.assertEqual(record["input_sha256"],sha256(OFFICE/"Editorial-Teal.potx"));self.assertEqual(record["slide_count"],10)
    def test_bridge_rejects_paths_outside_project(self):
        with self.assertRaises(ValueError):workspace_path(ROOT.parent/"outside.pptx")
    def test_bridge_does_not_overwrite_existing_directory(self):
        with self.assertRaises(FileExistsError):native_operation("catalog",OFFICE)
    def test_no_arbitrary_office_evaluation_operation(self):
        with self.assertRaises(ValueError):native_operation("arbitrary-python",ROOT/"runs/not-created")
    def test_smartart_limit_is_not_claimed_as_passed(self):
        record=json.loads((OFFICE/"office-worker.json").read_text(encoding="utf-8"))
        self.assertFalse(record["smartart_supported"]);self.assertTrue(record["smartart_error"])
        self.assertTrue(all(e["type"]!="smartart" for s in self.spec["slides"] for e in s["elements"]))


if __name__=="__main__":unittest.main()
