from pathlib import Path
from copy import deepcopy
import shutil,unittest
from tests import test_production_materials as fixture
from ppt_workflow import production_materials as m
from ppt_workflow.layout_capacity import COLORS
from ppt_workflow.paired_evidence import compile_compact_chart,prepare_compact_chart
from ppt_workflow.brief_composer import assemble,compose_brief

class PairedEvidenceTests(unittest.TestCase):
    setUp=fixture.ProductionMaterialsTests.setUp
    def compact_request(self):
        original=m.read(m.ROOT/'examples/chart-style-focus-comparison.json')
        return dict(version='compact-chart-request/1',slide_id='s1',element_id='small',theme=dict(font='Microsoft YaHei',colors={**COLORS,'secondary':'8498A2'}),chart=original['chart'],sources=original['sources'],facts=original['facts'],source_refs=original['source_refs'],heading='同题选择率（%）',source_note='来源：合成测试数据。')
    def composition(self):
        q=self.compact_request();fragment=compile_compact_chart(q);m.write(self.base/'compact.json',fragment)
        self.outline.update(sources=q['sources'],facts=q['facts']);m.write(self.base/'outline.json',self.outline)
        self.brief['slides'][0]['visuals'].append(dict(id='chart',kind='chart',required=True,purpose='测试双证据',composition_hint='图右比较',search_terms=[],source_refs=q['source_refs'],fact_refs=[f['id'] for f in q['facts']]))
        m.write(self.base/'brief.json',self.brief)
        self.plan['items'].append(dict(slide_id='s1',visual_id='chart',reason='Compact test fixture',files=[dict(role='source',path=str(self.base/'compact.json')),dict(role='preview',path=str(self.base/'selected/image.png'))]));m.write(self.base/'plan.json',self.plan)
        packed=m.build_pack(self.base/'plan.json',self.base/'素材');m.write(self.base/'design.json',dict(font='Microsoft YaHei',colors={**COLORS,'secondary':'8498A2'},layouts=[dict(key='image-chart',name='image-chart')]))
        return dict(version='brief-composition-request/1',job_id='pair-test',outline=str(self.base/'outline.json'),materials_pack=packed['manifest'],design_system=str(self.base/'design.json'),pages=[dict(slide_id='s1',visual_id='photo',chart_visual_id='chart',layout='image-chart',kicker='图片与比较',image_heading='场景参考',image_note='自建测试图片')])

    def test_pair_keeps_both_required_visuals_and_fact_bindings(self):
        spec,binding=assemble(self.composition());elements=spec['slides'][0]['elements']
        image=next(e for e in elements if e['type']=='image');chart=next(e for e in elements if e['type']=='chart')
        self.assertLess(image['rect']['x']+image['rect']['w'],chart['rect']['x'])
        self.assertEqual(set(binding['pages'][0]['visual_ids']),{'photo','chart'})
        self.assertEqual(binding['pages'][0]['unused_optional_visuals'],[])
        self.assertEqual(set(binding['pages'][0]['visual_elements_by_id']),{'photo','chart'})
        self.assertTrue(chart['fact_refs']);self.assertEqual(spec['facts'],self.outline['facts'])

    def test_wrong_values_and_excess_categories_fail_before_output(self):
        q=self.compact_request();q['chart']['series'][0]['values'][0]=1;m.write(self.base/'request.json',q)
        with self.assertRaisesRegex(ValueError,'fact/source mismatch'):prepare_compact_chart(self.base/'request.json',self.base/'out')
        self.assertFalse((self.base/'out').exists())
        q=self.compact_request();q['chart']['categories'].append('extra')
        with self.assertRaisesRegex(ValueError,'2–4'):compile_compact_chart(q)

    def test_unmatched_chart_id_is_not_silently_dropped(self):
        q=self.composition();q['pages'][0]['chart_visual_id']='missing'
        with self.assertRaisesRegex(ValueError,'required visuals'):assemble(q)

    def test_full_chart_is_not_implicitly_squeezed(self):
        q=self.composition();packed=m.read(q['materials_pack']);row=next(r for r in packed['items'] if r['visual_id']=='chart')
        # Directly test wrong prepared fragment type after a legitimate tracked snapshot.
        from unittest.mock import patch
        wrong=compile_compact_chart(self.compact_request());wrong['version']='chart-style-fragment/1'
        with patch('ppt_workflow.brief_composer.native_fragment',return_value=wrong):
            with self.assertRaisesRegex(ValueError,'shrink a full chart'):assemble(q)

    def test_real_native_chart_and_image_compile_together(self):
        q=self.composition();m.write(self.base/'composition.json',q)
        result=compose_brief(self.base/'composition.json',self.base/'composed',Path(shutil.which('node') or 'D:/node/node.exe'))
        self.assertTrue(Path(result['deck']).is_file());self.assertEqual(m.read(self.base/'composed/build/native-check.json')['status'],'passed')

if __name__=='__main__':unittest.main()
