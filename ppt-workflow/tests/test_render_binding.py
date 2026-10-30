import json
from pathlib import Path
import unittest
from ppt_workflow.qa.inspect import inspect_deck,bind_render
from ppt_workflow.contracts import validate

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless((ROOT/"runs/p1-real-probe/render/render-manifest.json").is_file(),"Local PowerPoint integration evidence is required; generate and render create_real_probe.py first")
class RenderBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/"runs/p1-real-probe/render/render-manifest.json").read_text(encoding="utf-8"))

    def test_real_target_bounds_confirm_long_word(self):
        result=bind_render(inspect_deck(ROOT/"runs/p1-real-probe/probe.pptx"),self.manifest)
        self.assertEqual([],validate(result.qa,"qa"))
        confirmed=[i for i in result.qa["issues"] if i["rule"]=="confirmed-text-overflow"]
        self.assertEqual(1,len(confirmed));self.assertEqual("slide-3",confirmed[0]["slide_id"])
        self.assertEqual("failed",result.qa["status"])
        self.assertEqual("passed",result.qa["stages"]["render"]["status"])

    def test_stale_input_hash_is_rejected(self):
        manifest=dict(self.manifest,input_sha256="0"*64)
        result=bind_render(inspect_deck(ROOT/"runs/p1-real-probe/probe.pptx"),manifest)
        self.assertEqual("failed",result.qa["stages"]["render"]["status"])
        self.assertIn("hash",result.qa["stages"]["render"]["evidence"][0])

    def test_partial_image_manifest_is_rejected(self):
        manifest=dict(self.manifest,images=self.manifest["images"][:1])
        result=bind_render(inspect_deck(ROOT/"runs/p1-real-probe/probe.pptx"),manifest)
        self.assertEqual("failed",result.qa["stages"]["render"]["status"])
        self.assertIn("count",result.qa["stages"]["render"]["evidence"][0])


if __name__=="__main__":unittest.main()
