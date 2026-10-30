"""Installer failures must happen before replacing files or creating environments."""
import hashlib,json,shutil,subprocess,sys,tempfile,unittest,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('PPT_WORKFLOW_NODE') or shutil.which('node') or 'D:/node/node.exe'
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'scripts').mkdir();(self.root/'vendor').mkdir()
        shutil.copy2(ROOT/'scripts/bootstrap.py',self.root/'scripts/bootstrap.py')
        self.wheel=self.root/'vendor/probe.whl';self.wheel.write_bytes(b'probe')
        (self.root/'vendor/manifest.json').write_text(json.dumps([{'path':'vendor/probe.whl','sha256':hashlib.sha256(b'probe').hexdigest()}]),encoding='utf-8')
    def run_bootstrap(self):
        return subprocess.run([sys.executable,'-X','utf8',str(self.root/'scripts/bootstrap.py'),'--node',NODE],capture_output=True,text=True,encoding='utf-8',timeout=20)
    def test_preview_does_not_create_environments(self):
        p=self.run_bootstrap();self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['status'],'preview');self.assertFalse((self.root/'.venv').exists())
    def test_modified_wheel_rejected_before_environment_creation(self):
        self.wheel.write_bytes(b'changed');p=self.run_bootstrap()
        self.assertNotEqual(p.returncode,0);self.assertIn('hash mismatch',p.stderr)
        self.assertFalse((self.root/'.venv').exists())
    def test_existing_environment_is_preserved(self):
        marker=self.root/'.venv/keep';marker.parent.mkdir();marker.write_text('unchanged',encoding='utf-8')
        p=self.run_bootstrap();self.assertNotEqual(p.returncode,0);self.assertIn('Existing environment',p.stderr)
        self.assertEqual(marker.read_text(encoding='utf-8'),'unchanged')
