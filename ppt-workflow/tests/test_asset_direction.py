from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_production_materials as fixture
from ppt_workflow import production_materials as m
from ppt_workflow.asset_direction import plan_assets,record_asset
from ppt_workflow.layout_capacity import plan_layout,compile_pages
from ppt_workflow.trend_annotations import compile_trend

class AssetDirectionTests(unittest.TestCase):
    setUp=fixture.ProductionMaterialsTests.setUp
    def configure(self):
        self.brief['asset_style']=dict(version='visual-style/1',id='solar-editorial',medium='photography',colors=dict(background='F8F5EE',ink='183341',accent='9B3045'),material='Natural surfaces',line='Native flat rules',tone='Clear daylight',references=[])
        self.direction=dict(role='context',medium='photography',subject='Rooftop solar array',aspect_ratio='16:9',negative_space='none',fit='contain',avoid=['Unrelated decorations'])
        self.brief['slides'][0]['visuals'][0]['visual_direction']=self.direction
        m.write(self.base/'brief.json',self.brief)
        m.write(self.base/'asset-plan-request.json',dict(version='asset-plan-request/1',outline=str(self.base/'outline.json'),brief=str(self.base/'brief.json')))
        p=plan_assets(self.base/'asset-plan-request.json',self.base/'planned')
        self.record=dict(version='asset-record-request/1',plan=p['plan'],slide_id='s1',visual_id='photo',preparation=str(self.base/'selected/preparation.json'),operation='existing',actual_tool='Unit-test fixture, not generation',actual_prompt='',actual_references=[],selection_reason='Relevant subject and full frame',review_notes='Fixture only')
        return p
    def recorded(self):
        m.write(self.base/'record.json',self.record)
        return record_asset(self.base/'record.json',self.base/'recorded')

    def test_shared_style_prompt_and_retrieval_are_plans_not_execution(self):
        result=self.configure();plan=m.read(result['plan']);task=plan['tasks'][0]
        self.assertIn('Natural surfaces',task['planned_prompt']);self.assertEqual(task['status'],'planned_not_executed')
        self.assertEqual(task['search']['orientation'],'landscape');self.assertTrue(task['generation_eligible'])

    def test_recorded_design_survives_existing_material_pack(self):
        self.configure();result=self.recorded();self.plan['items'][0]['preparation']=result['preparation'];m.write(self.base/'plan.json',self.plan)
        pack=m.build_pack(self.base/'plan.json',self.base/'素材');data,_=m.verify_pack(pack['manifest'],self.outline)
        prep=m.read(data['items'][0]['preparation']);self.assertEqual(prep['visual_design']['direction'],self.direction)
        self.assertEqual(prep['visual_design']['actual_prompt'],'')

    def test_style_change_rejects_stale_asset_before_pack_write(self):
        self.configure();result=self.recorded();self.plan['items'][0]['preparation']=result['preparation'];m.write(self.base/'plan.json',self.plan)
        self.brief['asset_style']['tone']='Different style';m.write(self.base/'brief.json',self.brief)
        with self.assertRaisesRegex(ValueError,'style does not match'):m.build_pack(self.base/'plan.json',self.base/'素材')
        self.assertFalse((self.base/'素材').exists())

    def test_template_style_file_does_not_rewrite_approved_brief(self):
        self.configure();style=self.brief.pop('asset_style');m.write(self.base/'brief.json',self.brief);original=(self.base/'brief.json').read_bytes()
        m.write(self.base/'style.json',style)
        m.write(self.base/'external-request.json',dict(version='asset-plan-request/1',outline=str(self.base/'outline.json'),brief=str(self.base/'brief.json'),style=str(self.base/'style.json')))
        planned=plan_assets(self.base/'external-request.json',self.base/'external-plan');self.record['plan']=planned['plan'];result=self.recorded()
        self.plan.update(asset_style=str(self.base/'style.json'));self.plan['items'][0]['preparation']=result['preparation'];m.write(self.base/'plan.json',self.plan)
        result=m.build_pack(self.base/'plan.json',self.base/'素材');data,_=m.verify_pack(result['manifest'],self.outline)
        self.assertEqual(m.read(data['asset_style']),style);self.assertEqual(original,(self.base/'brief.json').read_bytes())

    def test_generated_assets_cannot_replace_documentary_evidence(self):
        self.direction=None;self.configure();self.record.update(operation='generated',actual_prompt='Actual test prompt')
        plan=m.read(self.record['plan']);plan['tasks'][0]['design']['direction']['role']='evidence';m.write(Path(self.record['plan']),plan)
        with self.assertRaisesRegex(ValueError,'evidence'):self.recorded()

    def test_actual_prompt_not_invented_from_planned_prompt(self):
        self.configure();self.record.update(operation='generated')
        with self.assertRaisesRegex(ValueError,'actual submitted'):self.recorded()
        self.record['operation']='existing';self.record['actual_prompt']='Copied planned prompt'
        with self.assertRaisesRegex(ValueError,'do not have'):self.recorded()

    def test_actual_reference_images_are_snapshotted_and_packed(self):
        self.configure();self.record.update(operation='generated',actual_prompt='Actual unit-test prompt',actual_references=[str(self.base/'selected/image.png')])
        result=self.recorded();self.plan['items'][0]['preparation']=result['preparation'];m.write(self.base/'plan.json',self.plan)
        pack=m.build_pack(self.base/'plan.json',self.base/'素材');data,tracked=m.verify_pack(pack['manifest'],self.outline)
        target=Path(data['items'][0]['preparation']).parent/'reference-0.png';self.assertIn(target,tracked)
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):m.verify_pack(pack['manifest'],self.outline)

    def test_cache_obeys_geometry_filters(self):
        from ppt_workflow.online_assets import discover
        cache=self.base/'cache';folder=cache/'selected/fixture';folder.mkdir(parents=True)
        pixels=(self.base/'selected/image.png').read_bytes();(folder/'image.png').write_bytes(pixels)
        row=dict(id='solar-fixture',title='solar fixture',type='image',width=600,height=400,preview_url='',source_url='https://example.org/fixture',creator='Test',license='cc0')
        m.write(folder/'manifest.json',dict(row=row,files={'image.png':m.sha(pixels)}))
        with patch('ppt_workflow.online_assets.CACHE',cache):
            found=discover('solar',self.base/'found',provider='cache',orientation='landscape',min_width=500)
            result=discover('solar',self.base/'filtered',provider='cache',orientation='portrait',min_width=999999)
        self.assertEqual(len(found['assets']),1)
        self.assertEqual(result['assets'],[])

    def test_picture_story_has_separate_text_band_and_native_copy(self):
        q=dict(version='layout-request/1',slide_id='story',title='按画面组织说明',kicker='图片叙事',source_note='来源：自撰示例。',evidence='image',layout='image-story',blocks=[dict(id='see',heading='观察主体',text='先看屋顶阵列和周边环境。'),dict(id='explain',heading='解释用途',text='将图片与本页主张联系起来。')])
        plan=plan_layout(q);self.assertEqual(plan['page_count'],1)
        page=plan['pages'][0];self.assertLess(page['evidence_rect']['y']+page['evidence_rect']['h'],min(p['heading_rect']['y'] for p in page['parts']))
        self.assertTrue(all(e['type']=='text' for e in compile_pages(plan)['slides'][0]['elements']))

    def test_trend_notes_keep_category_fact_binding(self):
        request=m.read(m.ROOT/'examples/chart-style-focus-trend.json')
        q=dict(version='trend-annotation-request/1',chart_request=request,annotations=[dict(category='2026-01',text_template='方案甲 {fact:line-a-0}')])
        fragment=compile_trend(q);note=next(e for e in fragment['elements'] if e['id'].endswith('anno0-note'))
        self.assertEqual(note['fact_refs'],['line-a-0']);self.assertEqual(note['text'],'方案甲 48份')
        q['annotations'][0]['text_template']='方案甲 {fact:line-a-5}'
        with self.assertRaisesRegex(ValueError,'this category'):compile_trend(q)

if __name__=='__main__':unittest.main()
