"""Illustration origin and editable module semantics; not aesthetic scoring."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from PIL import Image
from ppt_workflow import illustration_library as art
from ppt_workflow.asset_library import search_assets
from ppt_workflow.module_library import search_modules,compile_module,prepare_module
ROOT=art.ROOT
class SceneModuleTests(unittest.TestCase):
    def request(self):return json.loads((ROOT/'examples/module-request.json').read_text(encoding='utf-8'))
    def test_curated_cc0_figures_and_original_search_compatibility(self):
        rows=art.load_illustrations()['assets'];self.assertEqual(2,len(rows));self.assertTrue(all('CC0-1.0' in r['license_note'] for r in rows));self.assertEqual(5,search_assets()['total_matches']);self.assertEqual(31,search_assets(asset_type='all')['total_matches'])
    def test_figure_search_does_not_impersonate_icon_or_photo(self):
        r=search_assets('交流',asset_type='illustration',style='open-peeps');self.assertEqual(2,r['total_matches']);self.assertTrue(all(a['type']=='illustration' for a in r['assets']));self.assertFalse(search_assets('真实现场',asset_type='illustration')['assets'])
    def test_illustration_preparation_keeps_alpha_aspect_and_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            r=art.prepare_illustration('peeps:peep-16',Path(t)/'out',size=512,slide_id='s1',element_id='person',reason='角色示意，非现场照片')
            with Image.open(r['files']['png']) as im:
                self.assertEqual(512,max(im.size));self.assertLess(im.width,im.height);self.assertEqual(0,im.getextrema()[-1][0])
            self.assertTrue(Path(r['files']['license']).is_file());self.assertEqual('peeps-peep-16',r['source']['id'])
            with self.assertRaises(ValueError):art.prepare_illustration('peeps:peep-16',Path(t)/'out',slide_id='s1',element_id='person',reason='duplicate')
    def test_illustration_recolor_and_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            with self.assertRaises(ValueError):art.prepare_illustration('peeps:peep-16',Path(t)/'out',color='FF0000',slide_id='s1',element_id='person',reason='invalid recolor')
            d=json.loads(art.CATALOG.read_text(encoding='utf-8'));d['assets'][0]['svg_sha256']='0'*64;p=Path(t)/'bad.json';p.write_text(json.dumps(d),encoding='utf-8')
            with patch.object(art,'CATALOG',p),self.assertRaises(ValueError):art.load_illustrations()
    def test_module_search_is_task_specific(self):
        self.assertEqual(4,search_modules()['total_matches']);self.assertEqual('native-comparison',search_modules('对比')['modules'][0]['id']);self.assertEqual(0,search_modules('水循环')['total_matches'])
    def test_module_fragment_is_native_and_retains_text(self):
        q=self.request();r=compile_module(q);text=[e['text'] for e in r['elements'] if e['type']=='text']
        for item in q['items']:
            self.assertIn(item['title'],text);self.assertIn(item['body'],text)
        self.assertTrue(all(e['type'] in ['text','line'] and e['editability_requirement']=='native' for e in r['elements']));self.assertEqual(['workflow'],r['source_refs'])
    def test_comparison_is_not_directional_and_action_requires_outputs(self):
        q=self.request();q['module_id']='native-comparison';q['items']=q['items'][:2]
        self.assertTrue(all(not e['arrow_end'] for e in compile_module(q)['elements'] if e['type']=='line'))
        q['module_id']='native-action'
        with self.assertRaises(ValueError):compile_module(q)
    def test_module_capacity_fails_without_shrinking(self):
        q=self.request();q['items'][0]['body']='过量文字'*10
        with self.assertRaisesRegex(ValueError,'capacity'):compile_module(q)
        q=self.request();q['rect']['w']=3
        with self.assertRaises(ValueError):compile_module(q)
        q=self.request();q['items'][0]['body']='a\n'*8
        with self.assertRaises(ValueError):compile_module(q)
    def test_timeline_requires_valid_ascending_dates(self):
        q=self.request();q['module_id']='native-timeline';q['items']=[dict(date='2026-10',title='资料',body='核对来源'),dict(date='2026-11',title='制作',body='整理图表')]
        r=compile_module(q);self.assertIn('2026-10',[e.get('text') for e in r['elements']])
        for dates in [('2026-12','2026-11'),('2026-10','2026-10'),('2026-13','2026-14')]:
            for item,d in zip(q['items'],dates):item['date']=d
            with self.subTest(dates=dates),self.assertRaises(ValueError):compile_module(q)
    def test_module_output_uses_fresh_directory_and_keeps_selection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            r=prepare_module(ROOT/'examples/module-request.json',Path(t)/'module');fragment=json.loads(Path(r['fragment']).read_text(encoding='utf-8'));self.assertEqual('s1',fragment['slide_id']);self.assertTrue(fragment['reason'])
            with self.assertRaises(ValueError):prepare_module(ROOT/'examples/module-request.json',Path(t)/'module')

if __name__=='__main__':unittest.main()
