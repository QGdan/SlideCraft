import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator
from ppt_workflow.contracts import validate, validate_bundle, SCHEMAS

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.brief, self.deck, self.qa = [json.loads((ROOT / "examples" / f"{kind}.json").read_text(encoding="utf-8")) for kind in ["brief", "deck", "qa"]]

    def test_schemas_are_valid(self):
        for path in SCHEMAS.glob("*.json"):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_valid_examples_and_bundle(self):
        for doc, kind in [(self.brief, "brief"), (self.deck, "deck"), (self.qa, "qa")]:
            self.assertEqual([], validate(doc, kind))
        self.assertEqual([], validate_bundle(self.brief, self.deck))

    def test_slide_count_rejects_outside_scope(self):
        self.brief["slide_count"] = 2
        self.assertTrue(validate(self.brief, "brief"))

    def test_template_requires_path(self):
        self.brief["theme"] = "provided_template"
        self.assertTrue(validate(self.brief, "brief"))

    def test_demo_source_cannot_be_declared_real(self):
        self.deck["facts"][0]["is_demo"] = False
        self.assertTrue(validate(self.deck, "deck"))

    def test_duplicate_element_ids(self):
        self.deck["slides"][1]["elements"][0]["id"] = self.deck["slides"][0]["elements"][0]["id"]
        self.assertTrue(validate(self.deck, "deck"))

    def test_unknown_fact_is_rejected(self):
        self.deck["slides"][1]["elements"][1]["fact_refs"] = ["missing"]
        self.assertTrue(validate(self.deck, "deck"))

    def test_chart_length_mismatch(self):
        self.deck["slides"][1]["elements"][1]["chart"]["series"][0]["values"] = [40]
        self.assertTrue(validate(self.deck, "deck"))

    def test_table_width_mismatch(self):
        self.deck["slides"][2]["elements"][1]["table"]["rows"][0] = ["manual"]
        self.assertTrue(validate(self.deck, "deck"))

    def test_nonfinite_values_rejected(self):
        self.deck["slides"][0]["elements"][0]["rect"]["x"] = float("nan")
        self.assertTrue(validate(self.deck, "deck"))

    def test_unverified_cannot_claim_pass(self):
        self.qa["status"] = "passed"
        self.assertTrue(validate(self.qa, "qa"))

    def test_complete_qa_contract_can_pass(self):
        self.qa["stages"] = {k: {"status": "passed", "evidence": ["contract-test-only"]} for k in self.qa["stages"]}
        self.qa["coverage"]["unknown"] = []
        self.qa["status"] = "passed"
        self.assertEqual([], validate(self.qa, "qa"))

    def test_unknown_coverage_cannot_hide_behind_passed_stages(self):
        self.qa["stages"] = {k: {"status": "passed", "evidence": ["contract-test-only"]} for k in self.qa["stages"]}
        self.qa["status"] = "passed"
        self.assertTrue(validate(self.qa, "qa"))

    def test_error_cannot_claim_pass(self):
        self.qa["stages"] = {k: {"status": "passed", "evidence": ["test-only"]} for k in self.qa["stages"]}
        self.qa["coverage"]["unknown"] = []
        self.qa["status"] = "passed"
        self.qa["issues"] = [{"id": "failure", "rule": "test", "severity": "error", "message": "known failure", "slide_id": None, "element_id": None, "evidence": ["test-only"]}]
        self.assertTrue(validate(self.qa, "qa"))

    def test_failed_stage_requires_failed_overall(self):
        self.qa["stages"]["render"]["status"] = "failed"
        self.assertTrue(validate(self.qa, "qa"))

    def test_bundle_detects_requested_page_mismatch(self):
        self.deck["slides"].pop()
        self.assertTrue(validate_bundle(self.brief, self.deck))

    def test_bundle_rejects_raster_required_chart(self):
        self.deck["slides"][1]["elements"][1]["editability_requirement"] = "raster_allowed"
        self.assertTrue(validate_bundle(self.brief, self.deck))

    def test_bundle_detects_changed_source(self):
        self.deck["sources"][0]["locator"] = "different provenance"
        self.assertTrue(validate_bundle(self.brief, self.deck))


if __name__ == "__main__":
    unittest.main()
