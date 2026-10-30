from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,tempfile,unittest,shutil
from lxml import etree
from ppt_workflow.relationships import compile_relationship,validate_relationship,wrap_native,ROOT
from ppt_workflow.contracts import validate
from ppt_workflow.content import inspect_native
from ppt_workflow.editorial_builder import build_editorial

class RelationshipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        slides=[]
        for i,kind in enumerate(['hierarchy','process','comparison'],1):
            q=json.loads((ROOT/'examples'/f'relationship-{kind}.json').read_text(encoding='utf-8'));fragment=compile_relationship(q)
            slides.append(dict(id=q['slide_id'],title=kind,message=kind,layout='takeaway',background_color='F8F5EE',source_refs=['workflow'],notes='Qualitative recipe fixture',elements=fragment['elements']))
        cls.spec=dict(schema_version='0.2',job_id='recipe-tests',canvas=dict(width=13.333,height=7.5,unit='in'),theme='provided_template',sources=[dict(id='workflow',kind='inline',locator='Qualitative self-authored workflow',is_demo=False)],facts=[],slides=slides)
        source=cls.base/'spec.json';source.write_text(json.dumps(cls.spec,ensure_ascii=False),encoding='utf-8')
        result=build_editorial(source,cls.base/'build',Path(shutil.which('node') or 'D:/node/node.exe'))
        cls.deck=Path(result['deck'])

    def request(self,kind='process'):
        return json.loads((ROOT/'examples'/f'relationship-{kind}.json').read_text(encoding='utf-8'))

    def test_explicit_process_order_and_source_are_required(self):
        q=self.request();m=q['relationship'];m['edges'].reverse()
        with self.assertRaisesRegex(ValueError,'reading order'):compile_relationship(q)
        q=self.request();q['relationship']['source_refs']=['unknown']
        with self.assertRaisesRegex(ValueError,'source'):validate_relationship(q['relationship'],{'workflow'})

    def test_hierarchy_rejects_cycles_and_unsupported_depth_without_dropping_nodes(self):
        q=self.request('hierarchy');q['relationship']['edges'][-1]={'from':'limits','to':'report'}
        with self.assertRaisesRegex(ValueError,'root-to-children'):compile_relationship(q)

    def test_comparison_requires_matching_dimensions(self):
        q=self.request('comparison');del q['relationship']['nodes'][1]['cells']['主要元素']
        with self.assertRaisesRegex(ValueError,'every shared'):compile_relationship(q)

    def test_chinese_latin_copy_is_not_silently_clipped(self):
        original='材料进入PowerPoint之后仍然可以继续修改'
        wrapped,_=wrap_native(original,3,18)
        self.assertEqual(wrapped.replace('\n',''),original)
        self.assertIn('\n',wrapped)
        q=self.request();q['relationship']['nodes'][0]['body']='长正文必须完整保留，不能偷偷删掉。'*20
        with self.assertRaisesRegex(ValueError,'capacity|wider'):compile_relationship(q)

    def test_scene_contract_rejects_dangling_native_connector(self):
        spec=deepcopy(self.spec)
        line=next(e for e in spec['slides'][0]['elements'] if e.get('connection'))
        line['connection']['to_id']='absent-shape'
        self.assertTrue(any('endpoints' in error for error in validate(spec,'deck')))

    def test_real_output_contains_bound_connectors_and_semantic_groups(self):
        report=inspect_native(self.deck,self.spec)
        self.assertEqual(report.status,'passed',report.issues)
        with ZipFile(self.deck) as z:
            ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            page=etree.fromstring(z.read('ppt/slides/slide1.xml'))
            self.assertEqual(len(page.findall('.//p:grpSp',ns)),1)
            self.assertEqual(len(page.findall('.//p:cxnSp',ns)),3)
            self.assertEqual(len(page.findall('.//a:stCxn',ns)),3)

    def test_changed_connector_binding_is_detected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            changed=Path(tmp)/'changed.pptx'
            with ZipFile(self.deck) as zin,ZipFile(changed,'w',ZIP_DEFLATED) as zout:
                for info in zin.infolist():
                    data=zin.read(info.filename)
                    if info.filename=='ppt/slides/slide1.xml':
                        root=etree.fromstring(data);root.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}endCxn').set('id','9999');data=etree.tostring(root)
                    zout.writestr(info,data)
            self.assertIn('native-connector-mismatch',{i['rule'] for i in inspect_native(changed,self.spec).issues})

    def test_semantic_placeholder_is_rejected_before_output(self):
        spec=deepcopy(self.spec);e=spec['slides'][0]['elements'][0];e.update(type='diagram',diagram=dict(kind='process',nodes=['输入','输出']));e.pop('connection',None)
        p=self.base/'placeholder.json';p.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf-8');out=self.base/'placeholder-out'
        with self.assertRaisesRegex(ValueError,'expanded native'):build_editorial(p,out,Path('D:/node/node.exe'))
        self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
