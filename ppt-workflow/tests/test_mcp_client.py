"""Validate invalid CLI calls before any MCP/COM work or evidence overwrite."""
from pathlib import Path
import subprocess,tempfile,unittest,sys
ROOT=Path(__file__).resolve().parents[1]
PY=Path(sys.executable)
class MCPClientTests(unittest.TestCase):
    def invoke(self,*args):
        return subprocess.run([str(PY),str(ROOT/'scripts/office_mcp_client.py'),*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
    def test_no_arguments_show_usage(self):
        result=self.invoke();self.assertEqual(result.returncode,2);self.assertIn('usage:',result.stderr)
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            marker=Path(temp)/'mcp-client.json';marker.write_text('keep',encoding='utf-8')
            result=self.invoke('health',temp)
            self.assertEqual(result.returncode,2);self.assertIn('already exists',result.stderr);self.assertEqual(marker.read_text(),'keep')
    def test_enhance_requires_input_before_opening_office(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            output=Path(temp)/'new';result=self.invoke('enhance',output)
            self.assertEqual(result.returncode,2);self.assertIn('require exactly one input',result.stderr);self.assertFalse(output.exists())
