from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from ppt_workflow import production_materials as m
from ppt_workflow import stages
from ppt_workflow.assets import register_asset

class ProductionMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=m.ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.outline=dict(narrative='技术测试',source_review_notes='仅测试合同',sources=[dict(id='s',kind='inline',locator='Synthetic source',is_demo=True)],facts=[],slides=[dict(id='s1',takeaway='逐页内容先明确',evidence_refs=[],speaker_intent='说明内容',visual_intent='示意图片')])
        self.brief=dict(version='production-brief/1',slides=[dict(id='s1',takeaway='逐页内容先明确',body_blocks=['内容段落已写好，不留待自动填充'],speaker_notes='讲解这页的信息结构',visuals=[dict(id='photo',kind='image',required=True,purpose='提供本页需要的场景',composition_hint='主图与文字分区，保留主体',search_terms=['classroom'],source_refs=[],fact_refs=[])])])
        m.write(self.base/'brief.json',self.brief);self.outline['production_brief']=str(self.base/'brief.json');m.write(self.base/'outline.json',self.outline)
        prepared=self.base/'selected';prepared.mkdir();Image.new('RGB',(600,400),'white').save(prepared/'image.png')
        (prepared/'attribution.txt').write_text('TEST ONLY: self-created raster',encoding='utf-8')
        self.prep=dict(status='prepared',asset=register_asset(prepared/'image.png',asset_id='image',source_id='art',license_note='Self-created test fixture'),source=dict(id='art',kind='inline',locator='Self-created test image',is_demo=True))
        m.write(prepared/'preparation.json',self.prep)
        self.plan=dict(version='materials-plan/1',outline=str(self.base/'outline.json'),brief=str(self.base/'brief.json'),items=[dict(slide_id='s1',visual_id='photo',reason='适合本页场景',preparation=str(prepared/'preparation.json'))])
        m.write(self.base/'plan.json',self.plan)

    def pack(self):
        return m.build_pack(self.base/'plan.json',self.base/'素材')

    def test_detailed_brief_matches_outline(self):
        self.assertEqual(m.validate_brief(self.brief,self.outline),self.brief)

    def test_changed_headline_or_order_rejected(self):
        b=deepcopy(self.brief);b['slides'][0]['takeaway']='Changed'
        with self.assertRaises(ValueError):m.validate_brief(b,self.outline)

    def test_empty_copy_and_generic_visual_task_rejected(self):
        for change in [{'body_blocks':[]},{'speaker_notes':''},{'visuals':[]}]:
            b=deepcopy(self.brief);b['slides'][0].update(change)
            with self.assertRaises(ValueError):m.validate_brief(b,self.outline)
        b=deepcopy(self.brief);b['slides'][0]['visuals'][0]['purpose']=''
        with self.assertRaises(ValueError):m.validate_brief(b,self.outline)

    def test_chart_requires_approved_facts(self):
        b=deepcopy(self.brief);b['slides'][0]['visuals'][0]['kind']='chart'
        with self.assertRaisesRegex(ValueError,'approved facts'):m.validate_brief(b,self.outline)

    def test_unknown_refs_and_duplicate_ids_rejected(self):
        b=deepcopy(self.brief);b['slides'][0]['visuals'][0]['source_refs']=['missing']
        with self.assertRaises(ValueError):m.validate_brief(b,self.outline)
        b=deepcopy(self.brief);b['slides'][0]['visuals']*=2
        with self.assertRaises(ValueError):m.validate_brief(b,self.outline)

    def test_pack_copies_assets_to_task_and_rebinds_preparation(self):
        result=self.pack();pack,tracked=m.verify_pack(result['manifest'],self.outline)
        row=pack['items'][0];prepared=m.read(row['preparation'])
        self.assertEqual(prepared['asset'],row['asset']);self.assertIn('素材',row['asset']['path'])
        self.assertNotEqual(prepared['asset']['id'],self.prep['asset']['id'])
        self.assertEqual(self.prep,m.read(self.base/'selected/preparation.json'))
        self.assertFalse(result['release_allowed']);self.assertGreater(len(tracked),3)

    def test_required_missing_rejected_before_writing(self):
        self.plan['items']=[];m.write(self.base/'plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'not prepared'):self.pack()
        self.assertFalse((self.base/'素材').exists())

    def test_unknown_or_duplicate_material_rejected(self):
        self.plan['items']*=2;m.write(self.base/'plan.json',self.plan)
        with self.assertRaises(ValueError):self.pack()

    def test_changed_packed_bytes_rejected(self):
        r=self.pack();pack=m.read(r['manifest']);Path(pack['items'][0]['asset']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):m.verify_pack(r['manifest'],self.outline)

    def test_changed_outline_rejected(self):
        r=self.pack();changed=deepcopy(self.outline);changed['narrative']='Another task'
        with self.assertRaises(ValueError):m.verify_pack(r['manifest'],changed)

    def test_native_visual_needs_source_and_preview(self):
        b=deepcopy(self.brief);b['slides'][0]['visuals'][0]['kind']='diagram';m.write(self.base/'brief.json',b)
        self.plan['items'][0]={'slide_id':'s1','visual_id':'photo','reason':'关系表达','files':[{'role':'source','path':str(self.base/'brief.json')}]};m.write(self.base/'plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'preview'):self.pack()

    def test_visual_sources_can_append_without_changing_facts(self):
        spec={'sources':self.outline['sources']+[self.prep['source']],'facts':[],'assets':[self.prep['asset']]}
        self.assertTrue(m.composition_sources_match(spec,self.outline))
        spec['sources'][0]={**spec['sources'][0],'locator':'changed'}
        self.assertFalse(m.composition_sources_match(spec,self.outline))

    def test_unregistered_origin_and_fact_change_rejected(self):
        spec={'sources':self.outline['sources']+[self.prep['source']],'facts':[],'assets':[]}
        self.assertFalse(m.composition_sources_match(spec,self.outline))
        spec={'sources':self.outline['sources'],'facts':[{'id':'invented'}],'assets':[]}
        self.assertFalse(m.composition_sources_match(spec,self.outline))

    def test_new_mode_outline_requires_real_brief(self):
        up={'intake':{'payload':{'slide_count':1,'production_mode':m.MODE}}}
        bad=deepcopy(self.outline);del bad['production_brief']
        with self.assertRaisesRegex(ValueError,'production_brief'):stages.validate_stage('outline',bad,self.base,up)
        files,missing=stages.validate_stage('outline',self.outline,self.base,up)
        self.assertIn(self.base/'brief.json',files);self.assertEqual(missing,[])

    def test_new_mode_template_cannot_skip_material_pack(self):
        up={'intake':{'payload':{'production_mode':m.MODE}}}
        with self.assertRaisesRegex(ValueError,'materials'):stages.validate_stage('template',{},self.base,up)

    def test_legacy_outline_remains_compatible(self):
        o=deepcopy(self.outline);del o['production_brief']
        files,missing=stages.validate_stage('outline',o,self.base,{'intake':{'payload':{'slide_count':1}}})
        self.assertEqual((files,missing),([],[]))

    def test_command_owned_by_composition_skill(self):
        self.assertEqual(stages.skill_route('material-pack')['skill'],'ppt-compose')

    def template_payload(self):
        from pptx import Presentation
        Presentation().save(self.base/'template.pptx')
        m.write(self.base/'design.json',dict(font='Microsoft YaHei',colors={'ink':'162E3B'},layouts=[dict(key='takeaway',name='Blank')]))
        return dict(selection_rationale='Synthetic template fixture',asset_guidance='Prepared materials first',editability_policy='Native text and replaceable image',
            materials_pack=self.pack()['manifest'],template_path=str(self.base/'template.pptx'),design_system=str(self.base/'design.json'),layout_keys=['takeaway'],preview_paths=[str(self.base/'selected/image.png')])

    def test_new_mode_template_tracks_complete_pack(self):
        p=self.template_payload();up={'intake':{'payload':{'production_mode':m.MODE}},'outline':{'payload':self.outline,'base_dir':str(self.base)}}
        files,missing=stages.validate_stage('template',p,self.base,up)
        packed=m.read(p['materials_pack']);self.assertIn(Path(packed['items'][0]['asset']['path']),files)
        self.assertEqual(missing,[])

    def test_template_pack_cannot_replace_approved_brief(self):
        p=self.template_payload();up={'intake':{'payload':{'production_mode':m.MODE}},'outline':{'payload':self.outline,'base_dir':str(self.base)}}
        with (self.base/'brief.json').open('a',encoding='utf-8') as f:f.write('\n')
        with self.assertRaisesRegex(ValueError,'approved detailed brief'):stages.validate_stage('template',p,self.base,up)

    def packed_spec(self):
        pack=m.read(self.pack()['manifest']);item=pack['items'][0]
        spec=dict(sources=[item['source']],assets=[item['asset']],slides=[dict(id='s1',elements=[dict(type='image',asset_id=item['asset']['id'])])])
        return pack,spec

    def test_composition_uses_prepared_image_and_source(self):
        pack,spec=self.packed_spec();m.validate_packed_images(spec,pack)
        spec['sources'][0]={**spec['sources'][0],'locator':'Wrong source'}
        with self.assertRaises(ValueError):m.validate_packed_images(spec,pack)

    def test_composition_cannot_omit_required_prepared_image(self):
        pack,spec=self.packed_spec();spec['slides'][0]['elements']=[]
        with self.assertRaisesRegex(ValueError,'omitted'):m.validate_packed_images(spec,pack)

    def test_composition_cannot_move_image_to_unapproved_page(self):
        pack,spec=self.packed_spec();spec['slides'][0]['id']='s2'
        with self.assertRaisesRegex(ValueError,'this page'):m.validate_packed_images(spec,pack)
