from pathlib import Path
from copy import deepcopy
import shutil,unittest
from tests import test_production_materials as fixture
from ppt_workflow import production_materials as m
from ppt_workflow.layout_capacity import COLORS
from ppt_workflow.editorial_frames import compile_frame,prepare_frame
from ppt_workflow.brief_composer import assemble,compose_brief

class EditorialFrameTests(unittest.TestCase):
    setUp=fixture.ProductionMaterialsTests.setUp
    def request(self,kind='cover'):
        frame=dict(kind=kind,kicker='方案汇报',footer='示意数据，非实测；原生模板测试。')
        if kind=='divider':frame['section_label']='01'
        if kind=='closing':frame['headings']=['整理资料']
        return dict(version='editorial-frame-request/1',slide_id='s1',element_id='frame1',theme=dict(font='Microsoft YaHei',colors=COLORS),frame=frame,content=dict(title=self.brief['slides'][0]['takeaway'],body_blocks=self.brief['slides'][0]['body_blocks']),source_refs=['s'])
    def packed(self,kind='cover'):
        q=self.request(kind);fragment=compile_frame(q);path=self.base/'frame.json';m.write(path,fragment)
        visual=self.brief['slides'][0]['visuals'][0];visual.update(kind='diagram',source_refs=['s'],editorial_frame=q['frame']);m.write(self.base/'brief.json',self.brief)
        self.plan['items'][0]=dict(slide_id='s1',visual_id='photo',reason='原生整页模板',files=[dict(role='source',path=str(path)),dict(role='preview',path=str(self.base/'selected/image.png'))]);m.write(self.base/'plan.json',self.plan)
        pack=m.build_pack(self.base/'plan.json',self.base/'素材');m.write(self.base/'design.json',dict(font='Microsoft YaHei',colors=COLORS,layouts=[dict(key=kind,name=kind)]))
        return dict(version='brief-composition-request/1',job_id='frame-fixture',outline=str(self.base/'outline.json'),materials_pack=pack['manifest'],design_system=str(self.base/'design.json'),pages=[dict(slide_id='s1',visual_id='photo',layout=kind,kicker=q['frame']['kicker'])])

    def test_three_frames_preserve_original_copy_and_native_visuals(self):
        for kind in ('cover','divider','closing'):
            f=compile_frame(self.request(kind));self.assertEqual(f['content']['body_blocks'],self.brief['slides'][0]['body_blocks'])
            self.assertTrue(any(e['type']=='shape' for e in f['elements']))
            self.assertTrue(all(e['editability_requirement']=='native' for e in f['elements']))
            ids=f['body_bindings'][0]['element_ids'];self.assertEqual(len(ids),1)
            text=next(e['text'] for e in f['elements'] if e['id']==ids[0]);self.assertEqual(text.replace('\n',''),self.brief['slides'][0]['body_blocks'][0])

    def test_long_copy_and_unmatched_actions_fail_without_writing(self):
        q=self.request();q['content']['body_blocks']=['必须保留长内容。'*80];m.write(self.base/'request.json',q)
        with self.assertRaises(ValueError):prepare_frame(self.base/'request.json',self.base/'out')
        self.assertFalse((self.base/'out').exists())
        q=self.request('closing');q['frame']['headings']=['标题甲','标题乙']
        with self.assertRaisesRegex(ValueError,'correspond'):compile_frame(q)

    def test_prepared_frame_is_bound_to_original_brief(self):
        request=self.packed();spec,_=assemble(request);self.assertEqual(spec['slides'][0]['layout'],'cover')
        pack=m.read(request['materials_pack']);e=next(e for e in spec['slides'][0]['elements'] if e['id']=='frame1-body0');e['text']='Changed'
        with self.assertRaisesRegex(ValueError,'frame copy'):m.validate_packed_images(spec,pack)

    def test_source_fragment_with_changed_copy_cannot_enter_pack(self):
        q=self.request();self.brief['slides'][0]['visuals'][0].update(kind='diagram',source_refs=['s'],editorial_frame=q['frame']);m.write(self.base/'brief.json',self.brief)
        q['content']['body_blocks']=['Changed source'];m.write(self.base/'frame.json',compile_frame(q));self.plan['items'][0]=dict(slide_id='s1',visual_id='photo',reason='测试',files=[dict(role='source',path=str(self.base/'frame.json')),dict(role='preview',path=str(self.base/'selected/image.png'))]);m.write(self.base/'plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'original body'):m.build_pack(self.base/'plan.json',self.base/'素材')
        self.assertFalse((self.base/'素材').exists())
        q=self.request();fragment=compile_frame(q);next(e for e in fragment['elements'] if e['id']=='frame1-body0')['text']='Changed actual text';m.write(self.base/'frame.json',fragment)
        with self.assertRaisesRegex(ValueError,'body objects'):m.build_pack(self.base/'plan.json',self.base/'素材')

    def test_frame_compiles_through_existing_generic_handoff(self):
        q=self.packed('closing');m.write(self.base/'composition-request.json',q)
        result=compose_brief(self.base/'composition-request.json',self.base/'composed',Path(shutil.which('node') or 'D:/node/node.exe'))
        self.assertTrue(Path(result['deck']).is_file())
        self.assertEqual(m.read(self.base/'composed/build/native-check.json')['status'],'passed')
        self.assertEqual(m.read(result['composition'])['deck_spec'],result['spec'])

if __name__=='__main__':unittest.main()
