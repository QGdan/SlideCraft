import json,os,subprocess,tempfile,unittest
from pathlib import Path
from pptx import Presentation
ROOT=Path(__file__).resolve().parents[1]

class EditorialDesignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.spec={'job_id':'native-template-test','canvas':{'width':13.333,'height':7.5},'slides':[{'id':'s1','title':'Probe','layout':'cover','background_color':'F8F5EE','notes':'TEST ONLY','elements':[]}]}
        self.design={'font':'Microsoft YaHei','layouts':[{'key':'cover','name':'Material Cover'},{'key':'process','name':'Material Process'}]}
    def build(self,design=True):
        (self.base/'spec.json').write_text(json.dumps(self.spec),encoding='utf-8');(self.base/'design.json').write_text(json.dumps(self.design),encoding='utf-8')
        cmd=[os.environ.get('PPT_WORKFLOW_NODE','D:/node/node.exe'),str(ROOT/'engine/editorial_build.cjs'),str(self.base/'spec.json'),str(self.base/'deck.pptx')]
        if design:cmd.append(str(self.base/'design.json'))
        return subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    def test_explicit_native_names_survive_pptx(self):
        r=self.build();self.assertEqual(r.returncode,0,r.stderr);p=Presentation(self.base/'deck.pptx')
        self.assertEqual(p.slides[0].slide_layout.name,'Material Cover')
        self.assertIn('Material Process',[l.name for m in p.slide_masters for l in m.slide_layouts])
    def test_unknown_layout_rejected(self):
        self.spec['slides'][0]['layout']='unknown';r=self.build();self.assertNotEqual(r.returncode,0);self.assertFalse((self.base/'deck.pptx').exists())
    def test_duplicate_native_names_rejected(self):
        self.design['layouts'][1]['name']='Material Cover';self.assertNotEqual(self.build().returncode,0)
    def test_legacy_without_design_stays_default(self):
        r=self.build(False);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(Presentation(self.base/'deck.pptx').slides[0].slide_layout.name,'DEFAULT')
    def test_validated_builder_normalizes_package_and_keeps_raw(self):
        from ppt_workflow.editorial_builder import build_editorial
        from ppt_workflow.qa.package import check_package
        self.spec.update(schema_version='0.2',theme='provided_template',sources=[{'id':'source','kind':'inline','locator':'Self-created test text','is_demo':False}],facts=[])
        self.spec['canvas']['unit']='in'
        self.spec['slides'][0].update(message='Probe',source_refs=['source'])
        self.spec['slides'].append({**self.spec['slides'][0],'id':'s2'})
        for page in self.spec['slides']:
            page['elements']=[dict(id=page['id']+'-title',type='text',role='title',rect=dict(x=1,y=1,w=8,h=1),editability_requirement='native',fact_refs=[],text='Probe')]
        source=self.base/'input.json';source.write_text(json.dumps(self.spec),encoding='utf-8')
        design=self.base/'style.json';design.write_text(json.dumps(self.design),encoding='utf-8')
        r=build_editorial(source,self.base/'built',os.environ.get('PPT_WORKFLOW_NODE','D:/node/node.exe'),design)
        self.assertEqual(r['status'],'built');self.assertTrue(Path(r['raw']).is_file())
        self.assertGreater(r['normalization_edits'],0)
        self.assertFalse([i for i in check_package(r['deck']).issues if i['severity']=='error'])
        self.assertEqual(Presentation(r['deck']).slides[0].slide_layout.name,'Material Cover')
    def test_validated_builder_rejects_invalid_input_before_output(self):
        from ppt_workflow.editorial_builder import build_editorial
        source=self.base/'invalid.json';source.write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):build_editorial(source,self.base/'not-created','D:/node/node.exe')
        self.assertFalse((self.base/'not-created').exists())
