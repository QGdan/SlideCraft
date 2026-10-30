"""Regression: supported nonnegative chart data must not be clipped by a fixed axis."""
from pathlib import Path
import json,shutil,subprocess,tempfile,unittest,os
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from ppt_workflow.unified import unified_deck
from ppt_workflow.workflow import ROOT,check_input,WorkflowError,read
NODE=os.environ.get('PPT_WORKFLOW_NODE') or shutil.which('node') or ('D:/node/node.exe' if Path('D:/node/node.exe').is_file() else None)
class ChartScaleTests(unittest.TestCase):
    def test_negative_values_are_explicitly_rejected(self):
        spec,_=unified_deck()
        next(e['chart'] for s in spec['slides'] for e in s['elements'] if e['type']=='chart')['series'][0]['values']=[-1,1]
        with self.assertRaisesRegex(WorkflowError,'nonnegative'):
            check_input(read(ROOT/'examples/brief.json')|{'job_id':spec['job_id'],'slide_count':10,'sources':spec['sources'],'theme':spec['theme']},spec)
    @unittest.skipUnless(NODE,'Node runtime required for real generation regression')
    def test_native_axis_preserves_baseline_and_covers_large_or_zero_values(self):
        for values,expected in [([40,1],46),([60,4],69),([0,0],1)]:
            with self.subTest(values=values),tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
                folder=Path(temp);spec,_=unified_deck()
                next(e['chart'] for s in spec['slides'] for e in s['elements'] if e['type']=='chart')['series'][0]['values']=values
                (folder/'spec.json').write_text(json.dumps(spec,ensure_ascii=False),encoding='utf-8')
                p=subprocess.run([NODE,str(ROOT/'engine/editorial_build.cjs'),str(folder/'spec.json'),str(folder/'deck.pptx')],cwd=ROOT,capture_output=True,timeout=40)
                self.assertEqual(p.returncode,0,p.stderr)
                with ZipFile(folder/'deck.pptx') as z:
                    chart=ET.fromstring(z.read('ppt/charts/chart1.xml'))
                ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
                self.assertEqual(float(chart.find('.//c:valAx/c:scaling/c:max',ns).get('val')),expected)
