"""Visual selection mechanics and same-content layout preservation."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from collections import Counter
from ppt_workflow import asset_library as library
from ppt_workflow.blueprints import compile_blueprint
from ppt_workflow.exhibits import compose_vertical_action
ROOT=Path(__file__).resolve().parents[1]
class VisualAssetTests(unittest.TestCase):
    def test_curated_assets_are_unique_with_duplicate_aliases(self):
        rows=library.load_library()['assets'];self.assertEqual(5,len(rows));self.assertEqual(5,len({r['sha256'] for r in rows}));self.assertEqual(2,sum(len(r['aliases']) for r in rows))
    def test_subject_use_and_style_filter(self):
        r=library.search_assets('校园',use='process',style='campus-editorial');self.assertEqual(['campus-service'],[a['id'] for a in r['assets']])
    def test_transparent_cutout_is_not_background_or_chart_evidence(self):
        r=library.search_assets('审核',use='spot');self.assertEqual(1,r['total_matches']);self.assertTrue(r['assets'][0]['transparent']);self.assertEqual('contain',r['assets'][0]['preferred_fit'])
        self.assertFalse(library.search_assets('审核',use='data-evidence')['assets'])
    def test_resolution_filter_returns_no_fabricated_match(self):self.assertFalse(library.search_assets(min_width=20000)['assets'])
    def test_empty_query_browses_library(self):self.assertEqual(5,library.search_assets()['total_matches'])
    def test_changed_asset_metadata_rejected(self):
        data=json.loads(library.CATALOG.read_text(encoding='utf-8'));data['assets'][0]['sha256']='0'*64
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            p=Path(t)/'catalog.json';p.write_text(json.dumps(data),encoding='utf-8')
            with patch.object(library,'CATALOG',p),self.assertRaises(ValueError):library.load_library()
    def test_gallery_has_real_local_images_and_fresh_outputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            out=Path(t)/'gallery';files=library.write_gallery(library.search_assets('校园'),out)
            page=Path(files['html']).read_text(encoding='utf-8');self.assertIn('campus-service.png',page);self.assertIn('校园协作服务场景',page)
            with self.assertRaises(ValueError):library.write_gallery(library.search_assets(),out)
    def test_invalid_search_limits_rejected(self):
        for kwargs in ({'limit':0},{'min_width':0}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):library.search_assets(**kwargs)
    def test_same_content_two_layouts(self):
        request=json.loads((ROOT/'examples/layout-comparison.json').read_text(encoding='utf-8'));spec,design=compile_blueprint(request,ROOT/'examples')
        def text(s):return Counter(e['text'] for e in s['elements'] if e['type']=='text' and not e['id'].endswith('-page'))
        self.assertEqual(text(spec['slides'][0]),text(spec['slides'][1]));self.assertEqual(['photo_process','photo_process_side'],[s['layout'] for s in spec['slides']])
        images=[next(e for e in s['elements'] if e['type']=='image') for s in spec['slides']];self.assertEqual(images[0]['asset_id'],images[1]['asset_id']);self.assertNotEqual(images[0]['rect'],images[1]['rect'])
    def test_vertical_capacity_rejects_dense_rows(self):
        request=json.loads((ROOT/'examples/layout-comparison.json').read_text(encoding='utf-8'));request['slides'][1]['items'][0]['body']='密集文字'*20
        with self.assertRaisesRegex(ValueError,'capacity'):compile_blueprint(request,ROOT/'examples')
if __name__=='__main__':unittest.main()
