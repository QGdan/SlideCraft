"""Meaningful placement, template, provenance, capacity and native-layout checks."""
import copy,json,os,subprocess,tempfile,unittest,hashlib
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from pptx import Presentation
from ppt_workflow.blueprints import compile_blueprint,catalog,build_blueprint
from ppt_workflow.contracts import validate
from ppt_workflow.stages import _native_template
from ppt_workflow.quality import validate_layouts
ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('PPT_WORKFLOW_NODE','D:/node/node.exe')
class BlueprintTests(unittest.TestCase):
    def request(self):return json.loads((ROOT/'examples/campus-blueprint.json').read_text(encoding='utf-8'))
    def compile(self,r=None):return compile_blueprint(r or self.request(),ROOT/'examples')
    def image(self,fit,focus=None):
        js="const {compileImage}=require('./engine/image_compile.cjs');const e=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify(compileImage(e,{width_px:1600,height_px:900})))"
        e={'id':'asset','asset_path':'a.png','rect':{'x':2,'y':1,'w':4,'h':4},'image_fit':fit}
        if focus is not None:e['image_focus']=focus
        r=subprocess.run([NODE,'-e',js],cwd=ROOT,input=json.dumps(e),capture_output=True,text=True,timeout=10)
        return r
    def test_contain_preserves_aspect_and_centers(self):
        r=json.loads(self.image('contain').stdout);self.assertAlmostEqual(16/9,r['w']/r['h']);self.assertAlmostEqual(1.875,r['y']);self.assertEqual(4,r['w'])
    def test_cover_crops_from_focal_side(self):
        r=json.loads(self.image('cover',{'x':1,'y':.5}).stdout);self.assertEqual('crop',r['sizing']['type']);self.assertEqual(4,r['sizing']['w']);self.assertAlmostEqual(r['w']-4,r['sizing']['x'])
    def test_unknown_fit_rejected(self):self.assertNotEqual(0,self.image('invented').returncode)
    def test_invalid_focus_rejected(self):self.assertNotEqual(0,self.image('cover',{'x':2,'y':.5}).returncode)
    def test_catalog_has_actual_template(self):self.assertIn('campus-editorial-v1',[r['id'] for r in catalog()])
    def test_registered_image_and_native_data(self):
        spec,design=self.compile();self.assertFalse(validate(spec,'deck'));self.assertEqual(4,len(spec['slides']))
        self.assertEqual(1,len(spec['assets']));self.assertIn('text_template',next(e for e in spec['slides'][1]['elements'] if e['id']=='p02-metric'))
        self.assertEqual(4,len(design['semantic_layouts']))
    def test_unknown_variant_rejected(self):
        r=self.request();r['variant']='ghost'
        with self.assertRaises(ValueError):self.compile(r)
    def test_oversize_content_rejected_instead_of_shrinking(self):
        r=self.request();r['slides'][0]['fields']['title']='太长'*30
        with self.assertRaisesRegex(ValueError,'capacity'):self.compile(r)
    def test_unknown_field_rejected(self):
        r=self.request();r['slides'][0]['fields']['typo']='test'
        with self.assertRaises(ValueError):self.compile(r)
    def test_missing_asset_rejected(self):
        r=self.request();r['assets']=[]
        with self.assertRaises(ValueError):self.compile(r)
    def test_assets_cannot_escape_project(self):
        r=self.request();r['assets'][0]['path']='../../../../../not-project.png'
        with self.assertRaisesRegex(ValueError,'inside project'):self.compile(r)
    def test_scene_without_disclosure_rejected(self):
        r=self.request();r['slides'][0]['fields']['footer']='真实照片'
        with self.assertRaisesRegex(ValueError,'disclosure'):self.compile(r)
    def test_chart_capacity_matches_real_layout(self):
        r=self.request();c=r['slides'][1]['chart'];c['categories']=['a']*7
        with self.assertRaisesRegex(ValueError,'capacity'):self.compile(r)
    def test_variant_changes_chart_and_native_text_tokens(self):
        r=self.request();r['variant']='ink';spec,design=self.compile(r)
        self.assertEqual('183247',spec['slides'][0]['background_color'])
        c=next(e for e in spec['slides'][1]['elements'] if e['type']=='chart')
        self.assertEqual(design['colors']['accent'],c['chart']['options']['colors']['accent'])
        self.assertEqual(6.65,spec['slides'][0]['elements'][0]['rect']['x'])
    def test_extended_layouts_require_blueprint_binding(self):
        spec,_=self.compile();del spec['blueprint_ref'];self.assertTrue(validate(spec,'deck'))
    def test_stale_blueprint_and_unbound_focus_are_rejected(self):
        spec,_=self.compile();spec['blueprint_ref']['sha256']='0'*64;self.assertTrue(validate(spec,'deck'))
        spec,_=self.compile();del spec['slides'][0]['elements'][0]['image_fit'];self.assertTrue(validate(spec,'deck'))
    def test_blueprint_and_fit_do_not_sneak_into_legacy(self):
        spec,_=self.compile();spec['schema_version']='0.1';self.assertTrue(validate(spec,'deck'))
    def test_build_native_masters_images_and_no_auto_release(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            out=Path(t)/'build';result=build_blueprint(ROOT/'examples/campus-blueprint.json',out,NODE)
            self.assertEqual('needs_review',result['status']);self.assertFalse(result['release_allowed']);self.assertFalse(result['native']['issues'])
            spec=json.loads((out/'deck-spec.json').read_text(encoding='utf-8'));design=json.loads((out/'design-system.json').read_text(encoding='utf-8'))
            _native_template(spec,out/'candidate.pptx',design)
            with ZipFile(out/'candidate.pptx') as z:
                hashes={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('ppt/media/')}
                self.assertIn(spec['assets'][0]['sha256'],hashes)
                root=E.fromstring(z.read('ppt/slides/slide4.xml'));ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
                crop=root.find('.//a:srcRect',ns);self.assertIsNotNone(crop);self.assertGreater(int(crop.get('l','0')),0)
            # Design metadata is usable by the actual quality-v1 layout validator.
            plan={'slides':[{'id':s['id'],'exhibit':{'carrier':design['semantic_layouts'][s['layout']]['carriers'][0]}} for s in spec['slides']]}
            self.assertFalse(validate_layouts(design,plan,spec))
            with self.assertRaises(ValueError):build_blueprint(ROOT/'examples/campus-blueprint.json',out,NODE)
if __name__=='__main__':unittest.main()
