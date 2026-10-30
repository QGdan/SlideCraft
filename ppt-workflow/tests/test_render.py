"""Renderer failure injection; mocked files are not Office success evidence."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import unittest
import uuid
from PIL import Image
from pptx import Presentation
from pptx.util import Inches
from ppt_workflow.render import render_deck,sha256,verify_images,powerpoint_lock,WorkerBusy

ROOT=Path(__file__).resolve().parents[1]


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT/"runs"/("p1-render-tests-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6])
        cls.root.mkdir(parents=True)
        cls.deck=cls.root/"two-slides.pptx"
        p=Presentation(); p.slide_width=Inches(13.333); p.slide_height=Inches(7.5)
        p.slides.add_slide(p.slide_layouts[6]);p.slides.add_slide(p.slide_layouts[6]);p.save(cls.deck)
        cls.records=[]

    @classmethod
    def tearDownClass(cls):
        (cls.root/"test-results.json").write_text(json.dumps(cls.records,indent=2),encoding="utf-8")

    def setUp(self):
        self.out=self.root/self._testMethodName
        self.lock=self.root/(self._testMethodName+"-lock")

    def invoke(self,runner,renderer="libreoffice",find=None):
        report=render_deck(self.deck,self.out,renderer=renderer,runner=runner,find_tool=find or (lambda n:n),lock_path=self.lock)
        self.records.append({"test":self._testMethodName,"status":report["status"],"error":report["error"],"mocked":True})
        return report

    def fake_lo(self,*,count=2,size=(1600,900),failure_at=None,malformed=False):
        def runner(command,**kwargs):
            stage="pdf" if command[0]=="soffice" else "png"
            if stage==failure_at:return subprocess.CompletedProcess(command,7,"","injected failure")
            if stage=="pdf":
                (self.out/(self.deck.stem+".pdf")).write_bytes(b"mock PDF")
            else:
                for index in range(count):
                    target=self.out/"slides"/f"slide-{index+1}.png"
                    if malformed:target.write_bytes(b"not an image")
                    else:Image.new("RGB",size,"white").save(target)
            return subprocess.CompletedProcess(command,0,"","mocked")
        return runner

    def fake_com(self,*,cleanup=True,count=2,hash_match=True,returncode=0):
        def runner(command,**kwargs):
            folder=Path(command[command.index("-OutDir")+1]);folder.mkdir()
            for index in range(count):Image.new("RGB",(1600,900),"white").save(folder/f"slide-{index+1:03d}.png")
            report=Path(command[command.index("-Report")+1])
            report.write_text(json.dumps({"status":"exported","slideCount":2,"inputSha256":sha256(self.deck) if hash_match else "0"*64,"cleanupCompleted":cleanup,"cleanupError":None if cleanup else "injected"}),encoding="utf-8")
            return subprocess.CompletedProcess(command,returncode,"","mocked")
        return runner

    def test_01_missing_pdftoppm_is_failure(self):
        report=self.invoke(lambda *a,**k:self.fail("Converter must not run"),find=lambda n:None if n=="pdftoppm" else n)
        self.assertEqual("failed",report["status"])

    def test_02_nonzero_pdf_conversion_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_lo(failure_at="pdf"))["status"])

    def test_03_nonzero_png_conversion_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_lo(failure_at="png"))["status"])

    def test_04_missing_pages_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_lo(count=1))["status"])

    def test_05_bad_dimensions_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_lo(size=(10,10)))["status"])

    def test_06_bad_png_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_lo(malformed=True))["status"])

    def test_07_mock_success_has_verified_files(self):
        report=self.invoke(self.fake_lo())
        self.assertEqual("passed",report["status"]);self.assertEqual(2,len(report["images"]))

    def test_08_stale_directory_is_refused(self):
        self.out.mkdir();marker=self.out/"old.txt";marker.write_text("unchanged")
        self.assertEqual("failed",self.invoke(lambda *a,**k:self.fail("Must not run"))["status"])
        self.assertEqual("unchanged",marker.read_text())

    def test_09_timeout_cannot_pass(self):
        def runner(*a,**k):raise subprocess.TimeoutExpired(a[0],60)
        self.assertEqual("unverified",self.invoke(runner)["status"])

    def test_10_powerpoint_timeout_quarantines_worker(self):
        def runner(*a,**k):raise subprocess.TimeoutExpired(a[0],60)
        self.assertEqual("unverified",self.invoke(runner,"powerpoint")["status"])
        self.assertTrue((self.lock/"quarantine.json").exists())

    def test_11_existing_lock_is_retained(self):
        self.lock.mkdir();marker=self.lock/"other-task.txt";marker.write_text("busy")
        self.assertEqual("needs_review",self.invoke(lambda *a,**k:self.fail("Must not run"),"powerpoint")["status"])
        self.assertTrue(marker.exists())

    def test_12_com_cleanup_failure_quarantines(self):
        self.assertEqual("failed",self.invoke(self.fake_com(cleanup=False),"powerpoint")["status"])
        self.assertTrue((self.lock/"quarantine.json").exists())

    def test_13_com_input_hash_mismatch_is_failure(self):
        self.assertEqual("failed",self.invoke(self.fake_com(hash_match=False),"powerpoint")["status"])

    def test_14_mock_com_success_releases_owned_lock(self):
        self.assertEqual("passed",self.invoke(self.fake_com(),"powerpoint")["status"])
        self.assertFalse(self.lock.exists())

    def test_15_zero_exit_with_no_worker_evidence_quarantines(self):
        self.assertEqual("failed",self.invoke(lambda c,**k:subprocess.CompletedProcess(c,0,"",""),"powerpoint")["status"])
        self.assertTrue((self.lock/"quarantine.json").exists())

    def test_16_no_pdf_after_zero_exit_is_failure(self):
        self.assertEqual("failed",self.invoke(lambda c,**k:subprocess.CompletedProcess(c,0,"",""))["status"])

    def test_17_duplicate_page_indices_rejected(self):
        self.out.mkdir()
        for name in ["slide-1.png","slide-01.png"]:Image.new("RGB",(1600,900)).save(self.out/name)
        with self.assertRaises(ValueError):verify_images(self.out,2,1600,900)

    def test_18_input_changed_during_render_is_failure(self):
        other=self.root/"changed-input.pptx";other.write_bytes(self.deck.read_bytes())
        self.deck=other
        normal=self.fake_lo()
        def runner(c,**k):
            result=normal(c,**k)
            if c[0]=="pdftoppm":other.write_bytes(other.read_bytes()+b"modified")
            return result
        report=render_deck(other,self.out,renderer="libreoffice",runner=runner,find_tool=lambda n:n)
        self.assertEqual("failed",report["status"])
        self.assertIn("Input changed",report["error"])


if __name__=="__main__":unittest.main()
