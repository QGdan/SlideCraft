import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from ppt_workflow import online_assets as a
from ppt_workflow.asset_placement import place

class OnlineAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=a.ROOT/'runs')
        self.base=Path(self.temp.name)
        self.cache=patch.object(a,'CACHE',self.base/'cache');self.cache.start()

    def tearDown(self):
        self.cache.stop();self.temp.cleanup()

    def icon_response(self):
        return {'icons':['tabler:car','tabler:car-filled'],
                'collections':{'tabler':{'total':6238,'version':'test','license':{'spdx':'MIT','url':'https://example.org/license'},'author':{'name':'Tabler'}}}}

    def search(self):
        with patch.object(a,'download',return_value=json.dumps(self.icon_response()).encode()):
            return a.discover('汽车',self.base/'search',provider='iconify')

    def photo_search(self):
        response={'results':[{'id':'image-1','title':'Car research','url':'https://example.org/car.png','thumbnail':'https://example.org/thumb.png','foreign_landing_url':'https://example.org/record','creator':'Example author','license':'by','license_url':'https://creativecommons.org/licenses/by/4.0/','license_version':'4.0','width':1200,'height':800}], 'next':None}
        with patch.object(a,'download',return_value=json.dumps(response).encode()):
            return a.discover('汽车',self.base/'search',provider='openverse')

    def photo(self):
        self.photo_search();b=io.BytesIO();Image.new('RGB',(1200,800),'#456789').save(b,format='PNG')
        with patch.object(a,'download',return_value=b.getvalue()):
            return a.fetch(self.base/'search/results.json','openverse:image-1',self.base/'prepared')

    def request(self,prep):
        deck={'schema_version':'0.2','job_id':'placement-test','canvas':{'width':13.333,'height':7.5,'unit':'in'},'theme':'provided_template','sources':[{'id':'fixture','kind':'inline','locator':'Technical fixture','is_demo':True}],'facts':[],
              'slides':[{'id':'s1','title':'Materials','message':'Materials','layout':'takeaway','background_color':'F8F5EE','notes':'Technical fixture','source_refs':['fixture'],'elements':[{'id':'title','type':'text','role':'title','rect':{'x':.5,'y':.5,'w':10,'h':1},'editability_requirement':'native','fact_refs':[],'text':'素材验证'}]}]}
        a.write(self.base/'deck.json',deck)
        q={'version':'asset-placement/1','deck':str(self.base/'deck.json'),'preparation':prep['preparation'],'slide_id':'s1','element_id':'hero','rect':{'x':1,'y':2,'w':7,'h':4},'credit_rect':{'x':1,'y':6.2,'w':10,'h':.4},'fit':'cover','focus':{'x':.4,'y':.5},'reason':'汽车主题与页面内容对应'}
        a.write(self.base/'request.json',q);return q

    def test_explicit_keyword_translation(self):
        self.assertEqual(a.expanded_query('汽车'),'car')
        self.assertEqual(a.expanded_query('难以翻译的主题','industrial robot'),'industrial robot')
        with self.assertRaises(ValueError):a.expanded_query('难以翻译的主题')

    def test_live_metadata_normalization_and_outline_family(self):
        result=self.search()
        self.assertEqual([x['id'] for x in result['assets']],['iconify:tabler:car'])
        self.assertEqual(result['providers'][0]['collection_size_reported'],6238)
        self.assertFalse(result['release_allowed'])

    def test_offline_exact_query_and_integrity(self):
        self.search()
        with patch.object(a,'download',side_effect=AssertionError('No network offline')):
            self.assertEqual(a.discover('汽车',self.base/'offline',provider='iconify',offline=True)['status'],'available')
            self.assertEqual(a.discover('教育',self.base/'missing',provider='iconify',offline=True)['status'],'failed')
        cache=next((a.CACHE/'queries').glob('*.json'));d=a.read(cache);d['response']['icons']=[];a.write(cache,d)
        self.assertEqual(a.discover('汽车',self.base/'changed',provider='iconify',offline=True)['status'],'failed')

    def test_partial_provider_failure_visible(self):
        def fake(provider,*args):
            if provider=='openverse':raise OSError('timeout')
            return {'provider':provider,'status':'available','assets':[{'id':'x','type':'icon','preview_url':'https://example.org/x','title':'Car','creator':'A','license':'MIT','source_url':'https://example.org/'}]}
        with patch.object(a,'provider_search',side_effect=fake):r=a.discover('汽车',self.base/'partial')
        self.assertEqual(r['status'],'partial');self.assertIn('timeout',r['providers'][1]['error'])

    def test_bad_limits_and_output(self):
        for kw in [{'limit':21},{'page':0},{'provider':'other'}]:
            with self.assertRaises(ValueError):a.discover('car',self.base/'x',**kw)
        with self.assertRaises(ValueError):a.fresh(a.ROOT/'assets')

    def test_private_or_non_https_url_rejected(self):
        for u in ['http://example.org/a','file:///a','https://user:pass@example.org/a','https://127.0.0.1/a']:
            with self.assertRaises(ValueError):a.public_url(u)

    def test_svg_external_and_active_content_rejected(self):
        for svg in [b'<svg><script/></svg>',b'<svg><image href="https://example.org"/></svg>',b'<svg><path fill="url(https://example.org)"/></svg>',b'<svg onload="x"/>']:
            with self.assertRaises(ValueError):a.safe_svg(svg,'123456')
        self.assertIn(b'#123456',a.safe_svg(b'<svg><path fill="currentColor"/></svg>','123456'))

    def test_photo_cache_reuse_checks_bytes(self):
        r=self.photo()
        with patch.object(a,'download',side_effect=AssertionError('Offline')):
            copy=a.fetch(self.base/'search/results.json','openverse:image-1',self.base/'reuse',offline=True)
        self.assertTrue(copy['cache_hit']);self.assertEqual(r['asset']['sha256'],copy['asset']['sha256'])
        cache=Path(r['cache_manifest']).parent;(cache/'image.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'cache changed'):
            a.fetch(self.base/'search/results.json','openverse:image-1',self.base/'tampered',offline=True)

    def test_unknown_id_and_missing_attribution_rejected(self):
        self.photo_search();path=self.base/'search/results.json';d=a.read(path)
        with self.assertRaises(ValueError):a.fetch(path,'missing',self.base/'x')
        d['assets'][0]['creator']='';a.write(path,d)
        with self.assertRaisesRegex(ValueError,'creator'):a.fetch(path,'openverse:image-1',self.base/'x')

    def test_html_not_accepted_as_photo(self):
        self.photo_search()
        with patch.object(a,'download',return_value=b'<html>not image</html>'):
            with self.assertRaises(OSError):a.fetch(self.base/'search/results.json','openverse:image-1',self.base/'invalid')

    def test_place_preserves_original_and_adds_source_image_credit(self):
        prep=self.photo();self.request(prep);before=(self.base/'deck.json').read_bytes()
        r=place(self.base/'request.json',self.base/'placed');deck=a.read(r['deck_spec']);page=deck['slides'][0]
        self.assertEqual(before,(self.base/'deck.json').read_bytes())
        self.assertEqual([e['type'] for e in page['elements']],['text','image','text'])
        self.assertEqual(page['elements'][1]['image_focus'],{'x':.4,'y':.5})
        self.assertEqual(page['source_refs'],['fixture',prep['source']['id']]);self.assertIn('Example author',page['notes'])

    def test_place_bounds_missing_credit_and_duplicate_rejected(self):
        prep=self.photo();q=self.request(prep)
        for change in [{'rect':{'x':12,'y':2,'w':7,'h':4}},{'element_id':'title'},{'focus':{'x':2,'y':0}}]:
            a.write(self.base/'request.json',{**q,**change})
            with self.assertRaises(ValueError):place(self.base/'request.json',self.base/'bad')
        del q['credit_rect'];a.write(self.base/'request.json',q)
        with self.assertRaisesRegex(ValueError,'credit_rect'):place(self.base/'request.json',self.base/'no-credit')

    def test_place_modified_preparation_bytes_rejected(self):
        prep=self.photo();self.request(prep);Path(prep['asset']['path']).write_bytes(b'bad')
        with self.assertRaises((ValueError,OSError)):place(self.base/'request.json',self.base/'placed')

    def test_cli_stage_routes(self):
        from ppt_workflow.stages import skill_route
        self.assertEqual(skill_route('asset-discover')['skill'],'ppt-template')
        self.assertEqual(skill_route('asset-fetch')['skill'],'ppt-compose')
        self.assertEqual(skill_route('asset-place')['skill'],'ppt-compose')

    def test_openverse_pagination_uses_page_count(self):
        response={'results':[],'page':1,'page_count':7}
        with patch.object(a,'download',return_value=json.dumps(response).encode()):
            result=a.discover('car',self.base/'paged',provider='openverse')
        self.assertEqual(result['providers'][0]['next_page'],2)

    def test_photo_orientation_and_minimum_resolution(self):
        self.photo_search()
        r=a.discover('汽车',self.base/'filtered',provider='openverse',offline=True,orientation='portrait')
        self.assertEqual(r['assets'],[])
        r=a.discover('汽车',self.base/'wide',provider='openverse',offline=True,orientation='landscape',min_width=1000)
        self.assertEqual(len(r['assets']),1)

    def test_selected_cache_can_be_searched_with_new_query(self):
        self.photo()
        with patch.object(a,'download',side_effect=AssertionError('No network')):
            r=a.discover('research',self.base/'cached-query',provider='cache',offline=True)
        self.assertEqual(r['assets'][0]['id'],'openverse:image-1')

    def test_commons_metadata_excludes_unsupported_licenses(self):
        def page(pid,license):
            return dict(pageid=pid,title='File:Solar.jpg',index=pid,imageinfo=[dict(url='https://upload.wikimedia.org/example.jpg',descriptionurl='https://commons.wikimedia.org/wiki/File:Solar.jpg',width=2000,height=1200,
                extmetadata={'LicenseShortName':{'value':license},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by/4.0/'},'Artist':{'value':'<a>Example author</a>'}})])
        response={'query':{'pages':{'1':page(1,'CC BY 4.0'),'2':page(2,'CC BY-SA 4.0')}}}
        with patch.object(a,'download',return_value=json.dumps(response).encode()):r=a.discover('光伏',self.base/'commons',provider='commons')
        self.assertEqual([x['id'] for x in r['assets']],['commons:1'])
        self.assertEqual(r['assets'][0]['creator'],'Example author')

    def test_empty_icon_results_not_misreported_as_license_error(self):
        with patch.object(a,'download',return_value=b'{"icons":[],"collections":{}}'):
            r=a.discover('nothingmatches',self.base/'empty',provider='iconify')
        self.assertEqual(r['providers'][0]['status'],'empty')

    def test_icon_pages_do_not_skip_undisplayed_candidates(self):
        data=self.icon_response();data['icons']=['tabler:item-'+str(n) for n in range(32)]
        with patch.object(a,'download',return_value=json.dumps(data).encode()):
            r=a.discover('car',self.base/'page2',provider='iconify',page=2,limit=8)
        self.assertIn('start=8',r['providers'][0]['request_url'])
        self.assertEqual(len(r['assets']),8)
