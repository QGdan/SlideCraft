"""Reject false positive direct-Office reports; mocks are not Office acceptance."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from pptx import Presentation
from PIL import Image
from ppt_workflow.render import sha256
ROOT=Path(__file__).resolve().parents[1]
module=importlib.util.spec_from_file_location('direct_render_verifier',ROOT/'scripts/verify_direct_render.py')
direct=importlib.util.module_from_spec(module);module.loader.exec_module(direct)

class DirectRenderTests(unittest.TestCase):
    def fixture(self,temp,**changes):
        out=Path(temp)/'out';out.mkdir();(out/'slides').mkdir()
        pptx=Path(temp)/'source.pptx';p=Presentation();p.slides.add_slide(p.slide_layouts[6]);p.save(pptx)
        Image.new('RGB',(1600,900),'white').save(out/'slides/slide-001.png')
        worker=dict(status='exported',cleanupCompleted=True,inputSha256=sha256(pptx),slideCount=1);worker.update(changes)
        (out/'powerpoint-worker.json').write_text(json.dumps(worker),encoding='utf-8')
        (out/'process.json').write_text(json.dumps(dict(returncode=0,timed_out=False)),encoding='utf-8')
        return pptx,out
    def test_complete_matching_evidence_creates_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            pptx,out=self.fixture(temp);r=direct.verify(pptx,out,1600,900)
            self.assertEqual('passed',r['status']);self.assertEqual(1,len(r['images']));self.assertEqual('not_implied_by_export',r['visual_review'])
            with self.assertRaisesRegex(ValueError,'Existing'):direct.verify(pptx,out,1600,900)
    def test_input_hash_mismatch_cannot_pass(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            pptx,out=self.fixture(temp,inputSha256='0'*64)
            with self.assertRaisesRegex(ValueError,'match'):direct.verify(pptx,out,1600,900)
            self.assertFalse((out/'render-manifest.json').exists())
    def test_cleanup_and_missing_slide_cannot_pass(self):
        for changes in ({'cleanupCompleted':False},{'slideCount':2}):
            with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
                pptx,out=self.fixture(temp,**changes)
                with self.assertRaises(ValueError):direct.verify(pptx,out,1600,900)
    def test_process_error_cannot_pass(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            pptx,out=self.fixture(temp);(out/'process.json').write_text(json.dumps(dict(returncode=2,timed_out=False)),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'process'):direct.verify(pptx,out,1600,900)
    def test_actual_image_size_checked(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            pptx,out=self.fixture(temp);Image.new('RGB',(10,10),'white').save(out/'slides/slide-001.png')
            with self.assertRaises(ValueError):direct.verify(pptx,out,1600,900)

if __name__=='__main__':unittest.main()
