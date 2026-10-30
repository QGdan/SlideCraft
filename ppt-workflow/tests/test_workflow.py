"""P3 lifecycle tests. Synthetic approvals here are test fixtures, not deck evidence."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from ppt_workflow import workflow as w
from ppt_workflow.qa.inspect import Inspection
from ppt_workflow.qa.common import CheckResult
from ppt_workflow.unified import unified_deck, PROFILE

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "runs/p2-unified-office-003/deck.pptx"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-p3-", dir=ROOT / "runs")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.marker = self.root / "engine.py"
        self.marker.write_text("engine-v1", encoding="utf-8")
        self.engines = patch.object(w, "engine_files", return_value=[self.marker])
        self.engines.start(); self.addCleanup(self.engines.stop)
        self.spec, _ = unified_deck()
        self.brief = w.read(ROOT / "runs/p2-unified-content-003/brief.json")
        self.spec_file, self.brief_file = self.root / "spec.json", self.root / "brief.json"
        w.write(self.spec_file, self.spec); w.write(self.brief_file, self.brief)
        self.config_file = self.root / "config.json"
        template = ROOT / "runs/p2-unified-template-003/Unified-Ivory.potx"
        self.config = {"spec": str(self.spec_file), "brief": str(self.brief_file), "template": str(template), "design_system": str(PROFILE),
                       "node": sys.executable, "design_approval": {"spec_sha256": w.sha256(self.spec_file), "template_sha256": w.sha256(template),
                       "design_sha256": w.sha256(PROFILE), "reviewer": "TEST FIXTURE", "evidence": "synthetic test authorization"}}
        w.write(self.config_file, self.config)
        self.run = self.root / "job"

    def plan(self):
        return w.plan(self.config_file, self.run)

    def built(self):
        self.plan()
        revision = self.run / "rev-000"
        shutil.copy2(BASELINE, revision / "deck.pptx")
        state = w.read(self.run / "state.json")
        state.update(status="built", deck_sha256=w.sha256(revision / "deck.pptx"))
        w.write(self.run / "state.json", state)
        return state, revision

    def rendered(self, revision):
        out = revision / "render-000"
        slides = out / "slides"
        slides.mkdir(parents=True)
        for n in range(1, 11):
            Image.new("RGB", (1600, 900), "white").save(slides / f"slide-{n:03d}.png")
        manifest = {"status": "passed", "input_sha256": w.sha256(revision / "deck.pptx"), "expected_slide_count": 10,
                    "width": 1600, "height": 900, "images": w.verify_images(slides, 10, 1600, 900), "worker": {}}
        w.write(out / "render-manifest.json", manifest)
        return manifest

    def mock_inspection(self):
        report = w.read(ROOT / "runs/p2-unified-office-003/qa.json")
        report["status"] = "unverified"
        report["coverage"]["unknown"] = ["visual-review-not-executed"]
        report["stages"] = {k: {"status": "passed", "evidence": ["SYNTHETIC TEST ONLY"]} for k in report["stages"]}
        report["stages"]["visual"]["status"] = "unverified"
        report["stages"]["visual"]["reason"] = "visual-review-not-executed"
        report["issues"] = []
        return Inspection(report, {"inventory": [], "measurements": [], "package": {"slide_parts": [str(n) for n in range(10)]}})

    def ready(self):
        state, revision = self.built()
        self.rendered(revision)
        inspection = self.mock_inspection()
        inspection.qa["artifact"] = {"path": str(revision / "deck.pptx"), "sha256": state["deck_sha256"]}
        with patch.object(w, "inspect_native", return_value=CheckResult(details={"mapping": []})), \
             patch.object(w, "inspect_deck", side_effect=lambda *a, **k: copy.deepcopy(inspection)), \
             patch.object(w, "bind_content", side_effect=lambda report, *a: report):
            first = w.qa(self.run)
            review = w.read(Path(first["qa_directory"]) / "review-request.json")
            review.update(status="passed", reviewer="TEST ONLY", consistency_notes="synthetic check", content_notes="synthetic check")
            for page in review["pages"]:
                page.update(status="passed", notes="SYNTHETIC TEST IMAGE; not actual visual approval")
            review_file = self.root / "review.json"
            w.write(review_file, review)
            result = w.qa(self.run, review_path=review_file)
        self.assertEqual(result["status"], "ready")
        return result, revision

    def test_plan_freezes_inputs_and_outline(self):
        state = self.plan()
        self.assertEqual(state["status"], "planned")
        self.assertEqual(len(w.read(self.run / "outline.json")), 10)
        self.assertEqual(w.load_job(self.run)[1]["input_digest"], state["input_digest"])

    def test_stale_design_approval_rejected_before_output(self):
        self.config["design_approval"]["spec_sha256"] = "0"*64
        w.write(self.config_file, self.config)
        with self.assertRaisesRegex(w.WorkflowError, "approval"):
            self.plan()
        self.assertFalse(self.run.exists())

    def test_eight_and_twenty_page_contracts_reuse_known_layouts(self):
        for count in (8, 20):
            deck = copy.deepcopy(self.spec)
            deck['slides'] = [copy.deepcopy(self.spec['slides'][i % 10]) for i in range(count)]
            for i, page in enumerate(deck['slides'], 1):
                page['id'] = f's{i:02d}'
                for j, element in enumerate(page['elements'], 1):
                    element['id'] = f's{i:02d}-e{j:02d}'
            brief = {**self.brief, 'slide_count': count}
            w.check_input(brief, deck)

    def test_unsupported_chart_is_rejected_instead_of_silently_becoming_bar(self):
        chart = next(e['chart'] for p in self.spec['slides'] for e in p['elements'] if e['type'] == 'chart')
        chart['kind'] = 'line'
        with self.assertRaisesRegex(w.WorkflowError, 'horizontal bar'):
            w.check_input(self.brief, self.spec)

    def test_arbitrary_output_directory_rejected(self):
        with self.assertRaisesRegex(w.WorkflowError, "runs"):
            w.plan(self.config_file, ROOT / "not-a-run")

    def test_input_spec_change_invalidates_plan(self):
        self.plan(); self.spec_file.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(w.WorkflowError, "review invalid"):
            w.load_job(self.run)
        self.assertEqual(w.read(self.run / "state.json")["status"], "needs_review")

    def test_revision_spec_change_invalidates_plan(self):
        self.plan(); (self.run / "rev-000/deck-spec.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(w.WorkflowError): w.load_job(self.run)

    def test_engine_change_invalidates_plan(self):
        self.plan(); self.marker.write_text("engine-v2", encoding="utf-8")
        with self.assertRaises(w.WorkflowError): w.load_job(self.run)

    def test_added_engine_file_invalidates_plan(self):
        self.plan()
        new = self.root / "new-engine.py"; new.write_text("new", encoding="utf-8")
        self.engines.stop()
        with patch.object(w, "engine_files", return_value=[self.marker, new]):
            with self.assertRaises(w.WorkflowError): w.load_job(self.run)

    def test_resolved_config_tampering_invalidates(self):
        self.plan(); c = w.read(self.run / "config.json"); c["node"] = "other"
        w.write(self.run / "config.json", c)
        with self.assertRaises(w.WorkflowError): w.load_job(self.run)

    def test_registered_asset_change_invalidates(self):
        asset = self.root / "hero.png"
        shutil.copy2(self.spec["assets"][0]["path"], asset)
        self.spec["assets"][0]["path"] = str(asset)
        next(e for e in self.spec["slides"][0]["elements"] if e["type"] == "image")["asset_path"] = str(asset)
        w.write(self.spec_file, self.spec)
        self.config["design_approval"]["spec_sha256"] = w.sha256(self.spec_file)
        w.write(self.config_file, self.config)
        self.plan(); asset.write_bytes(b"changed")
        with self.assertRaises(w.WorkflowError): w.load_job(self.run)

    def test_resume_is_idempotent_for_unchanged_deck(self):
        state, _ = self.built()
        with patch.object(w, "command", side_effect=AssertionError("should not execute")):
            self.assertEqual(w.build(self.run, resume=True)["deck_sha256"], state["deck_sha256"])

    def test_resume_rejects_tampered_pptx(self):
        _, revision = self.built(); (revision / "deck.pptx").write_bytes(b"tamper")
        with self.assertRaises(w.WorkflowError): w.build(self.run, resume=True)

    def test_environment_retry_is_bounded_and_logged(self):
        self.plan()
        with patch.object(w, "command", side_effect=FileNotFoundError("test missing runtime")):
            with self.assertRaises(w.WorkflowError): w.build(self.run)
            with self.assertRaises(w.WorkflowError): w.build(self.run)
            with self.assertRaises(w.WorkflowError): w.build(self.run, retry_environment=True)
            with self.assertRaisesRegex(w.WorkflowError, "limited to one"): w.build(self.run, retry_environment=True)
        state = w.read(self.run / "state.json")
        self.assertEqual(state["environment_retries"], 1)
        self.assertTrue((self.run / "rev-000/build-000/failure.json").is_file())
        self.assertTrue((self.run / "rev-000/build-001/failure.json").is_file())

    def test_job_lock_prevents_overlap(self):
        self.plan()
        with w.locked(self.run):
            with self.assertRaisesRegex(w.WorkflowError, "busy"):
                w.build(self.run)

    def test_review_must_cover_every_page_once(self):
        binding = {"value": "fixture"}
        review = {"binding": binding, "status": "passed", "reviewer": "test", "method": "host-image-inspection",
                  "pages": [{"slide": 1, "status": "passed", "notes": "test"}]*2, "consistency_notes": "test", "content_notes": "test"}
        with self.assertRaisesRegex(w.WorkflowError, "each page"):
            w.check_visual_review(review, binding, 2)

    def test_review_for_different_hash_is_rejected(self):
        with self.assertRaises(w.WorkflowError):
            w.check_visual_review({"binding": {"old": True}, "status": "passed", "reviewer": "test"}, {"new": True}, 10)

    def test_visual_binding_survives_second_qa_timestamp(self):
        state, _ = self.ready()
        self.assertEqual(state["qa_status"], "passed")
        self.assertTrue((Path(state["qa_directory"]) / "visual-review.json").is_file())

    def test_unverified_delivery_rejected_without_output(self):
        self.built()
        state = w.read(self.run / "state.json"); state.update(status="unverified", qa_status="unverified")
        w.write(self.run / "state.json", state)
        with self.assertRaisesRegex(w.WorkflowError, "not deliverable"):
            w.deliver(self.run, self.root / "delivery")
        self.assertFalse((self.root / "delivery").exists())

    def test_complete_synthetic_release_creates_hash_manifest_and_zip(self):
        self.ready()
        out = self.root / "delivery"
        result = w.deliver(self.run, out)
        self.assertEqual(result["status"], "delivered")
        for record in w.read(out / "manifest.json")["files"]:
            self.assertEqual(w.sha256(out / record["path"]), record["sha256"])
        self.assertTrue((out / "delivery.zip").is_file())

    def test_changed_qa_invalidates_delivery(self):
        state, _ = self.ready()
        (Path(state["qa_directory"]) / "qa.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(w.WorkflowError, "evidence changed"):
            w.deliver(self.run, self.root / "delivery")

    def test_changed_render_invalidates_delivery(self):
        state, revision = self.ready()
        (revision / "render-000/slides/slide-001.png").write_bytes(b"changed")
        with self.assertRaises(w.WorkflowError): w.deliver(self.run, self.root / "delivery")

    def test_corruption_during_copy_does_not_create_release_manifest(self):
        self.ready()
        out = self.root / "delivery"
        copy_file = shutil.copy2
        def corrupt(src, dst, *a, **k):
            result = copy_file(src, dst, *a, **k)
            if Path(dst) == out / "deck.pptx": Path(dst).write_bytes(b"copy corruption")
            return result
        with patch.object(w.shutil, "copy2", side_effect=corrupt):
            with self.assertRaisesRegex(w.WorkflowError, "copy verification"):
                w.deliver(self.run, out)
        self.assertFalse((out / "manifest.json").exists())
        self.assertFalse((out / "delivery.zip").exists())

    def test_benchmark_missing_metrics_remain_null(self):
        self.plan()
        row = w.benchmark([self.run])["runs"][0]
        self.assertIsNone(row["cost"]); self.assertIsNone(row["human_edit_seconds"])

    def test_visual_call_reservations_stop_at_three_even_without_success(self):
        state, _ = self.ready()
        tickets = [w.reserve_visual_call(self.run) for _ in range(3)]
        self.assertEqual(tickets[-1]["remaining"], 0)
        self.assertEqual(len({t["ticket"]["id"] for t in tickets}), 3)
        with self.assertRaisesRegex(w.WorkflowError, "budget exhausted"):
            w.reserve_visual_call(self.run)

    def test_visual_reservation_requires_rendered_qa(self):
        self.built()
        with self.assertRaises(w.WorkflowError): w.reserve_visual_call(self.run)

    def test_delivery_rejects_unresolved_warning(self):
        state, _ = self.ready()
        directory = Path(state["qa_directory"])
        report = w.read(directory / "qa.json")
        report["issues"].append({"id": "warning", "severity": "warning", "rule": "test-only"})
        w.write(directory / "qa.json", report)
        # Re-seal the synthetic fixture so this tests policy rather than integrity.
        state["qa_evidence"] = w.file_records([Path(x["path"]) for x in state["qa_evidence"]])
        w.write(self.run / "state.json", state)
        with self.assertRaisesRegex(w.WorkflowError, "unresolved warnings"):
            w.deliver(self.run, self.root / "delivery")

    def test_local_revision_creates_fresh_version_and_drops_review(self):
        state, revision = self.ready()
        patch_doc, qa_report, mapping = self.repair_fixture()
        directory = Path(state["qa_directory"])
        w.write(directory / "qa.json", qa_report)
        w.write(directory / "object-map.json", mapping)
        state.update(status="needs_review", qa_evidence=w.file_records([Path(x["path"]) for x in state["qa_evidence"]]))
        w.write(self.run / "state.json", state)
        original = w.sha256(revision / "deck-spec.json")
        patch_file = self.root / "repair.json"; w.write(patch_file, patch_doc)
        result = w.revise(self.run, patch_file)
        self.assertEqual(result["revision"], 1)
        self.assertEqual(result["status"], "planned")
        self.assertNotIn("qa_evidence", result)
        self.assertNotIn("deck_sha256", result)
        self.assertEqual(w.sha256(revision / "deck-spec.json"), original)
        self.assertTrue((self.run / "rev-001/repair.json").is_file())
        self.assertEqual(w.load_job(self.run)[1]["revision"], 1)

    def repair_fixture(self):
        element = next(e for e in self.spec["slides"][1]["elements"] if e["id"] == "s02-e07")
        rect = {**element["rect"], "h": element["rect"]["h"]+.15}
        patch_doc = {"changes": [{"element_id": element["id"], "issue_id": "overflow-1", "rect": rect}]}
        qa = {"issues": [{"id": "overflow-1", "element_id": "slide-2/shape-9", "rule": "confirmed-text-overflow"}]}
        mapping = {"mapping": [{"spec_id": element["id"], "output_id": "slide-2/shape-9"}]}
        return patch_doc, qa, mapping

    def test_evidenced_frame_expansion_preserves_all_content(self):
        patch_doc, qa, mapping = self.repair_fixture()
        result = w.revise_spec(self.spec, patch_doc, qa, mapping)
        a, b = copy.deepcopy(self.spec), copy.deepcopy(result)
        for spec in (a, b):
            for page in spec["slides"]:
                for e in page["elements"]: e.pop("rect", None)
        self.assertEqual(a, b)

    def test_repair_cannot_change_facts_or_fonts(self):
        p, q, m = self.repair_fixture(); p["changes"][0]["text"] = "claim changed"
        with self.assertRaisesRegex(w.WorkflowError, "content/data/brand"):
            w.revise_spec(self.spec, p, q, m)

    def test_repair_cannot_use_issue_from_another_object(self):
        p, q, m = self.repair_fixture(); q["issues"][0]["element_id"] = "other"
        with self.assertRaises(w.WorkflowError): w.revise_spec(self.spec, p, q, m)

    def test_repair_cannot_collide_with_another_object(self):
        p, q, m = self.repair_fixture(); p["changes"][0]["rect"]["w"] += .5
        self.spec["slides"][1]["elements"].append({"id": "blocker", "type": "text", "rect": {"x": 7.05, "y": 4.72, "w": .3, "h": .4}})
        with self.assertRaisesRegex(w.WorkflowError, "intersect"):
            w.revise_spec(self.spec, p, q, m)

    def test_repair_cannot_move_frame(self):
        p, q, m = self.repair_fixture(); p["changes"][0]["rect"]["x"] += .1
        with self.assertRaises(w.WorkflowError): w.revise_spec(self.spec, p, q, m)

    def test_two_revisions_is_a_hard_limit(self):
        self.plan(); state = w.read(self.run / "state.json"); state["revision"] = 2; w.write(self.run / "state.json", state)
        with self.assertRaisesRegex(w.WorkflowError, "Two content repair"):
            w.revise(self.run, self.root / "unused.json")


if __name__ == "__main__": unittest.main()
