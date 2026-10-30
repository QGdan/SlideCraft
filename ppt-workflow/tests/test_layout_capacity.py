from copy import deepcopy
import unittest
from ppt_workflow.textflow import measure_lines,measured_font,NO_START,NO_END
from ppt_workflow.layout_capacity import plan_layout,compile_pages

def request():
    return dict(version='layout-request/1',slide_id='body',title='真实内容决定页面布局',kicker='设计方法',source_note='来源：本项目自撰制作方法。',evidence='none',blocks=[dict(id='brief',heading='先准备内容',text='根据大纲整理图片、图表和说明，让每项素材服务于页面的主张。')])

class CapacityTests(unittest.TestCase):
    def test_cjk_punctuation_and_mixed_words_preserve_exact_source(self):
        original='中文（包含括号）的句子，需要保留标点；PowerPoint 与 WPS 可编辑。\n下一段保留 20% 的原始文字。'
        lines=measure_lines(original,2.6,19)
        self.assertEqual(''.join(original[x['start']:x['end']] for x in lines),original)
        for line in lines:
            self.assertNotIn(line['text'][:1],NO_START)
            self.assertNotIn(line['text'][-1:],NO_END)
            self.assertLessEqual(measured_font(19).getlength(line['text']), (2.6-.04)*144)
        self.assertTrue(any('PowerPoint' in x['text'] for x in lines))

    def test_wide_unbreakable_token_requests_another_region(self):
        with self.assertRaisesRegex(ValueError,'wider'):measure_lines('SuperLongUnbreakableToken'*8,2,19)

    def test_full_original_survives_multipage_allocation(self):
        q=request();q['blocks'][0]['text']*=45
        plan=plan_layout(q);self.assertGreater(plan['page_count'],1)
        self.assertEqual(''.join(p['source_text'] for page in plan['pages'] for p in page['parts']),q['blocks'][0]['text'])
        for page in plan['pages']:
            for p in page['parts']:self.assertLessEqual(p['body_rect']['y']+p['body_rect']['h'],6.67)
        self.assertEqual(len(compile_pages(plan)['slides']),plan['page_count'])

    def test_locked_page_count_keeps_copy_but_blocks_compilation(self):
        q=request();q['blocks'][0]['text']*=45;q['page_limit']=1
        plan=plan_layout(q);self.assertEqual(plan['status'],'needs_input')
        self.assertEqual(plan['source_request'],q)
        with self.assertRaisesRegex(ValueError,'author decision'):compile_pages(plan)

    def test_evidence_type_filters_candidates_and_reserves_geometry(self):
        q=request();q['evidence']='image';p=plan_layout(q)
        self.assertEqual({c['layout'] for c in p['candidates']},{'image-led','image-balanced','image-right','image-story'})
        f=compile_pages(p);self.assertTrue(f['evidence_slots'])
        self.assertFalse(any(e['type']=='image' for e in f['slides'][0]['elements']))
        q['evidence']='chart';q['blocks']=[];p=plan_layout(q)
        self.assertEqual(p['selected_layout'],'chart-focus')
        self.assertGreaterEqual(p['pages'][0]['evidence_rect']['w'],11.4)

    def test_explicit_layout_and_long_title_have_real_capacity_limits(self):
        q=request();q['layout']='image-led'
        with self.assertRaisesRegex(ValueError,'Requested layout'):plan_layout(q)
        q=request();q['title']='标题不能被偷偷裁掉'*30
        with self.assertRaisesRegex(ValueError,'No supported'):plan_layout(q)

    def test_no_silent_unknown_fields_or_missing_copy(self):
        q=request();q['summarize']=True
        with self.assertRaisesRegex(ValueError,'unknown'):plan_layout(q)
        q=request();q['blocks'][0]['text']=''
        with self.assertRaisesRegex(ValueError,'Actual'):plan_layout(q)

if __name__=='__main__':unittest.main()
