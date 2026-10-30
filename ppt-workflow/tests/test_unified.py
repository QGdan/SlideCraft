import copy
import json
import unittest
from pathlib import Path
from zipfile import ZipFile
from pptx import Presentation
from ppt_workflow.unified import unified_deck,check_unified_consistency,PROFILE
from ppt_workflow.content import inspect_native,check_ledger
from ppt_workflow.render import sha256

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=ROOT/"runs/p2-unified-content-003"
OFFICE=ROOT/"runs/p2-unified-office-003"
TEMPLATE=ROOT/"runs/p2-unified-template-003"
ART=ROOT/"runs/p2-unified-editable-002"


class UnifiedTests(unittest.TestCase):
    def setUp(self):self.deck,self.profile=unified_deck()
    def test_all_ten_layouts_share_frozen_design(self):self.assertEqual(check_unified_consistency(self.deck).status,"passed")
    def test_actual_office_headers_backgrounds_and_layouts_match(self):
        r=check_unified_consistency(self.deck,OFFICE/"deck.pptx");self.assertEqual(r.status,"passed",r.issues);self.assertEqual(len(r.details["native_headers"]),10)
    def test_dark_slide_drift_is_detected(self):
        self.deck["slides"][2]["background_color"]="102A38";self.assertIn("inconsistent-background",{i["rule"] for i in check_unified_consistency(self.deck).issues})
    def test_title_position_drift_is_detected(self):
        e=next(e for e in self.deck["slides"][0]["elements"] if e["role"]=="title");e["rect"]["y"]+=.1
        self.assertIn("inconsistent-shared-region",{i["rule"] for i in check_unified_consistency(self.deck).issues})
    def test_mismatched_title_font_is_detected(self):
        next(e for e in self.deck["slides"][1]["elements"] if e["role"]=="title")["style"]["font_size_pt"]=30
        self.assertIn("inconsistent-shared-font",{i["rule"] for i in check_unified_consistency(self.deck).issues})
    def test_image_cannot_cross_shared_header(self):
        next(e for e in self.deck["slides"][0]["elements"] if e["type"]=="image")["rect"]["y"]=1
        self.assertIn("artwork-outside-template-region",{i["rule"] for i in check_unified_consistency(self.deck).issues})
    def test_original_ledger_and_native_evidence_are_preserved(self):
        self.assertEqual(check_ledger(self.deck,ROOT).status,"passed");self.assertEqual(inspect_native(OFFICE/"deck.pptx",self.deck).status,"passed")
    def test_template_precedes_and_is_hash_bound_to_content(self):
        binding=json.loads((SAMPLE/"template-profile.json").read_text(encoding="utf-8"));self.assertEqual(sha256(TEMPLATE/"Unified-Ivory.potx"),binding["template_sha256"])
        self.assertEqual(sha256(PROFILE),binding["design_system_sha256"])
        self.assertLessEqual((TEMPLATE/"Unified-Ivory.potx").stat().st_mtime_ns,(SAMPLE/"deck-spec.json").stat().st_mtime_ns)
    def test_native_master_variants_have_different_real_slots(self):
        with ZipFile(TEMPLATE/"Unified-Ivory.potx") as z:
            self.assertIn(b"presentationml.template.main+xml",z.read("[Content_Types].xml"))
        # The template preview is a native PPTX copy with the same ten layouts.
        p=Presentation(TEMPLATE/"template-preview.pptx")
        counts=[len(s.slide_layout.shapes) for s in p.slides]
        self.assertGreater(len(set(counts)),1)
        self.assertEqual(len(p.slides),10)
        self.assertEqual(len(p.slide_masters[0].slide_layouts),10)
    def test_editable_module_contains_no_raster_children(self):
        p=Presentation(ART/"editable-components.pptx");group=next(s for s in p.slides[0].shapes if s.name=="Editable report review")
        self.assertEqual(len(group.shapes),12);self.assertFalse(any(s.shape_type==13 for s in group.shapes))
        self.assertTrue((ART/"report-review-editable.svg").read_text(encoding="utf-8").startswith('<svg'))
    def test_svg_is_structured_not_embedded_png(self):
        svg=(ART/"report-review-editable.svg").read_text(encoding="utf-8")
        self.assertIn('<text id="report-title"',svg);self.assertIn('<ellipse id="review-lens"',svg);self.assertNotIn('data:image',svg)
    def test_no_confirmed_render_overflow(self):
        q=json.loads((OFFICE/"qa.json").read_text(encoding="utf-8"));self.assertFalse(q["issues"]);self.assertEqual(q["stages"]["render"]["status"],"passed")


if __name__=="__main__":unittest.main()
