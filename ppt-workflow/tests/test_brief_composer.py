from copy import deepcopy
from pathlib import Path
import unittest,shutil
from tests import test_production_materials as fixture
from ppt_workflow import production_materials as m
from ppt_workflow.brief_composer import assemble,compose_brief
from ppt_workflow.layout_capacity import COLORS
from ppt_workflow.chart_style_library import compile_chart_style

class BriefComposerTests(unittest.TestCase):
    setUp=fixture.ProductionMaterialsTests.setUp
    def request(self):
        m.write(self.base/'plan.json',self.plan);pack=m.build_pack(self.base/'plan.json',self.base/'素材')
        design=dict(font='Microsoft YaHei',colors={**COLORS,'secondary':'8498A2'},layouts=[dict(key=k,name=k) for k in ['image-right','chart_takeaway']]);m.write(self.base/'design.json',design)
        return dict(version='brief-composition-request/1',job_id='brief-tests',outline=str(self.base/'outline.json'),materials_pack=pack['manifest'],design_system=str(self.base/'design.json'),pages=[dict(slide_id='s1',visual_id='photo',layout='image-right',kicker='内容组织',source_note='示意数据，非实测；自建测试图。',sections=[dict(body_index=0,heading='准备内容')])])

    def test_original_ids_headlines_body_and_facts_survive(self):
        spec,binding=assemble(self.request())
        self.assertEqual(spec['slides'][0]['id'],'s1');self.assertEqual(spec['slides'][0]['title'],self.outline['slides'][0]['takeaway'])
        original=self.brief['slides'][0]['body_blocks'][0];ids=binding['pages'][0]['body_blocks'][0]['element_ids']
        self.assertEqual(''.join(e['text'].replace('\n','') for e in spec['slides'][0]['elements'] if e['id'] in ids),original)
        self.assertEqual(spec['facts'],self.outline['facts'])

    def test_missing_page_or_body_block_rejected(self):
        q=self.request();q['pages']=[]
        with self.assertRaisesRegex(ValueError,'every outline'):assemble(q)
        request=dict(version='brief-composition-request/1',job_id='brief-tests',outline=str(self.base/'outline.json'),materials_pack=str(self.base/'素材/manifest.json'),design_system=str(self.base/'design.json'),pages=[dict(slide_id='s1',visual_id='photo',layout='image-right',kicker='内容',source_note='测试',sections=[])])
        with self.assertRaisesRegex(ValueError,'every body'):assemble(request)

    def test_unselected_required_visual_and_unapproved_layout_rejected(self):
        self.brief['slides'][0]['visuals'].append({**self.brief['slides'][0]['visuals'][0],'id':'other'})
        self.plan['items'].append({**self.plan['items'][0],'visual_id':'other'});m.write(self.base/'brief.json',self.brief)
        q=self.request()
        with self.assertRaisesRegex(ValueError,'Multiple required'):assemble(q)
        q['pages'][0]['layout']='unknown'
        with self.assertRaises(ValueError):assemble(q)

    def test_content_overflow_is_rejected_before_output(self):
        self.brief['slides'][0]['body_blocks'][0]*=50;m.write(self.base/'brief.json',self.brief);q=self.request();m.write(self.base/'request.json',q)
        with self.assertRaisesRegex(ValueError,'content needs'):compose_brief(self.base/'request.json',self.base/'result',Path(shutil.which('node')))
        self.assertFalse((self.base/'result').exists())

    def test_actual_compiler_output_and_handoff(self):
        q=self.request();m.write(self.base/'request.json',q)
        result=compose_brief(self.base/'request.json',self.base/'result',Path(shutil.which('node') or 'D:/node/node.exe'))
        self.assertTrue(Path(result['deck']).is_file());self.assertEqual(m.read(result['composition'])['deck_spec'],result['spec'])

    def test_one_body_block_mapping_survives_two_story_columns(self):
        self.brief['slides'][0]['body_blocks'][0]*=4;m.write(self.base/'brief.json',self.brief);q=self.request()
        design=m.read(self.base/'design.json');design['layouts'].append(dict(key='image-story',name='image-story'));m.write(self.base/'design.json',design);q['pages'][0]['layout']='image-story'
        spec,binding=assemble(q);ids=binding['pages'][0]['body_blocks'][0]['element_ids'];self.assertEqual(len(ids),2)
        actual=''.join(e['text'].replace('\n','') for e in spec['slides'][0]['elements'] if e['id'] in ids)
        self.assertEqual(actual,self.brief['slides'][0]['body_blocks'][0])

    def test_native_chart_uses_prepared_data_and_rejects_rebinding(self):
        cq=m.read(m.ROOT/'examples/chart-style-focus-comparison.json');cq.update(slide_id='s1',element_id='native-chart')
        cq['theme']['colors'].update(ink=COLORS['ink'],muted=COLORS['muted'])
        fragment=compile_chart_style(cq);m.write(self.base/'chart.json',fragment)
        self.outline.update(sources=cq['sources'],facts=cq['facts']);m.write(self.base/'outline.json',self.outline)
        v=self.brief['slides'][0]['visuals'][0];v.update(kind='chart',source_refs=cq['source_refs'],fact_refs=[f['id'] for f in cq['facts']]);m.write(self.base/'brief.json',self.brief)
        self.plan['items'][0]=dict(slide_id='s1',visual_id='photo',reason='Native fixture',files=[dict(role='source',path=str(self.base/'chart.json')),dict(role='preview',path=str(self.base/'selected/image.png'))])
        q=self.request();q['pages'][0]=dict(slide_id='s1',visual_id='photo',layout='chart_takeaway',kicker='数据')
        spec,_=assemble(q);self.assertEqual(next(e for e in spec['slides'][0]['elements'] if e['type']=='chart')['chart']['series'],cq['chart']['series'])
        # A deliberately changed outline cannot silently use an old packed chart.
        changed=deepcopy(self.outline);changed['facts'][0]['value']=1;m.write(self.base/'outline.json',changed)
        with self.assertRaisesRegex(ValueError,'another outline'):assemble(q)

if __name__=='__main__':unittest.main()
