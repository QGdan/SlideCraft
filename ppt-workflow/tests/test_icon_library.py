"""Pinned library integrity, meaningful search, and traceable per-page preparation."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from PIL import Image
from ppt_workflow import icon_library as icons
from ppt_workflow.asset_library import search_assets,write_gallery
from ppt_workflow.contracts import validate

class IconLibraryTests(unittest.TestCase):
    def test_pinned_unique_sources_and_license(self):
        rows=icons.load_icons()['assets'];self.assertEqual(24,len(rows));self.assertEqual(1,len({r['upstream_commit'] for r in rows}));self.assertTrue(all(r['style_family']=='tabler-outline' for r in rows))
    def test_existing_image_search_keeps_default(self):
        self.assertEqual(5,search_assets()['total_matches']);self.assertTrue(all(a['type']=='image' for a in search_assets()['assets']))
    def test_chinese_semantic_alias_research(self):
        r=search_assets('科研',asset_type='icon');self.assertIn('tabler:microscope',[a['id'] for a in r['assets']])
    def test_category_and_style_prevent_mixed_family(self):
        r=search_assets('学习',asset_type='all',category='education',style='tabler-outline');self.assertTrue(r['assets']);self.assertTrue(all(a['type']=='icon' for a in r['assets']))
    def test_all_types_and_no_fabricated_match(self):
        self.assertEqual(31,search_assets(asset_type='all')['total_matches']);self.assertEqual([],search_assets('火星矿井运输',asset_type='all')['assets'])
    def test_invalid_type(self):
        with self.assertRaises(ValueError):search_assets(asset_type='sound')
    def test_svg_tamper_refused(self):
        data=json.loads(icons.CATALOG.read_text(encoding='utf-8'));data['assets'][0]['svg_sha256']='0'*64
        with tempfile.TemporaryDirectory(dir=icons.ROOT/'runs') as t:
            catalog=Path(t)/'library.json';catalog.write_text(json.dumps(data),encoding='utf-8')
            with patch.object(icons,'CATALOG',catalog),self.assertRaisesRegex(ValueError,'changed'):icons.load_icons()
    def test_duplicate_id_refused(self):
        data=json.loads(icons.CATALOG.read_text(encoding='utf-8'));data['assets'][1]['id']=data['assets'][0]['id']
        with tempfile.TemporaryDirectory(dir=icons.ROOT/'runs') as t:
            catalog=Path(t)/'library.json';catalog.write_text(json.dumps(data),encoding='utf-8')
            with patch.object(icons,'CATALOG',catalog),self.assertRaisesRegex(ValueError,'Duplicate'):icons.load_icons()
    def test_actual_prepare_color_alpha_license_source_and_registration(self):
        with tempfile.TemporaryDirectory(dir=icons.ROOT/'runs') as t:
            r=icons.prepare_icon('tabler:school',Path(t)/'school',color='9B3045',size=128,slide_id='s1',element_id='s1-school',reason='教育主题节点')
            self.assertTrue(Path(r['files']['license']).is_file());self.assertIn('#9B3045',Path(r['files']['svg']).read_text(encoding='utf-8'));self.assertFalse(r['release_allowed'])
            with Image.open(r['files']['png']) as im:
                self.assertEqual((128,128),im.size);self.assertEqual(0,im.getpixel((0,0))[3]);self.assertTrue(any(p[:3]==(155,48,69) and p[3]>200 for p in im.getdata()))
            self.assertEqual('s1-school',r['selection']['element_id']);self.assertEqual('url',r['source']['kind'])
            # Existing production contract accepts the registered PNG/source fragment.
            example=json.loads((icons.ROOT/'examples/deck.json').read_text(encoding='utf-8'))
            example.setdefault('assets',[]).append(r['asset']);example['sources'].append(r['source'])
            self.assertEqual([],validate(example,'deck'))
            with self.assertRaises(ValueError):icons.prepare_icon('tabler:school',Path(t)/'school',slide_id='s1',element_id='icon',reason='重复目录')
    def test_bad_preparation_inputs_do_not_create_files(self):
        with tempfile.TemporaryDirectory(dir=icons.ROOT/'runs') as t:
            out=Path(t)/'bad'
            for kwargs in ({'color':'red'},{'size':1024},{'reason':''},{'slide_id':'bad:id'},{'asset_id':'tabler:missing'}):
                params=dict(asset_id='tabler:school',slide_id='s1',element_id='icon',reason='测试');params.update(kwargs)
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):icons.prepare_icon(out=out,**params)
                self.assertFalse(out.exists())
    def test_gallery_uses_actual_icon_previews(self):
        with tempfile.TemporaryDirectory(dir=icons.ROOT/'runs') as t:
            r=write_gallery(search_assets('科研',asset_type='icon'),Path(t)/'gallery');self.assertIn('microscope.png',Path(r['html']).read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
