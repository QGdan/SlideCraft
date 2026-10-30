"""Stage handoffs; all automated approvals below are explicitly TEST ONLY."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from ppt_workflow import stages as s
from ppt_workflow.workflow import ROOT, read, write, WorkflowError


class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='test-stage-', dir=ROOT/'runs')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.workspace = self.base/'handoffs'
        self.spec = read(ROOT/'runs/p2-unified-content-003/deck-spec.json')
        self.deck = ROOT/'runs/p3-unified-cli-003/rev-000/deck.pptx'
        self.requirements = {'topic':'教学报告自动化','audience':'教研组','goal':'决定是否试点','language':'zh-CN',
                             'delivery_mode':'presented','slide_count':10,'aspect_ratio':'16:9',
                             'brand':'暖白青绿','editability':'文字、图表、表格和流程原生','open_questions':[]}
        self.outline = {'narrative':'试点目标、责任边界、证据和审批', 'source_review_notes':'TEST ONLY: baseline demo records retained',
                        'sources':self.spec['sources'],'facts':self.spec['facts'],
                        'slides':[{'id':p['id'],'takeaway':p['title'],'evidence_refs':p['source_refs'],
                                   'speaker_intent':'说明这一页的论点','visual_intent':'沿用已确认版式'} for p in self.spec['slides']]}
        self.template = {'template_path':str(ROOT/'runs/p2-unified-template-003/Unified-Ivory.potx'),
                         'design_system':str(ROOT/'templates/unified-v3/design-system.json'),
                         'preview_paths':[str(ROOT/'runs/p3-unified-cli-003/rev-000/render-000/slides/slide-001.png')],
                         'layout_keys':[x['key'] for x in read(ROOT/'templates/unified-v3/design-system.json')['layouts']],
                         'selection_rationale':'统一暖白风格','asset_guidance':'暖白青绿同材质','editability_policy':'原生数据对象'}
        self.compose = {'deck':str(self.deck),'deck_spec':str(ROOT/'runs/p2-unified-content-003/deck-spec.json'),
                        'implementation_notes':'TEST ONLY: actual baseline artifacts, no new construction claimed'}
        self.polish = {'deck':str(self.deck),'deck_spec':self.compose['deck_spec'],'visual_notes':'TEST ONLY: same baseline',
                       'copy_notes':'no copy changes in fixture','changes':[]}
        q = Path(read(ROOT/'runs/p3-unified-cli-003/state.json')['qa_directory'])
        self.review = {'qa_report':str(q/'qa.json'),'automated_qa':str(q/'automated-qa.json'),
                       'render_manifest':str(q/'render-manifest.json'),'visual_review':str(q/'visual-review.json'),
                       'decision':'unverified','assessment':'Actual automated unknown checks remain unresolved'}
        self.payloads = {'intake':self.requirements,'outline':self.outline,'template':self.template,
                         'compose':self.compose,'polish':self.polish,'review':self.review}

    def submit(self, stage, payload=None, *, approve=True):
        path = self.base/f'{stage}-input.json'
        write(path,self.payloads[stage] if payload is None else payload)
        result = s.stage_action(stage,self.workspace,input_path=path)
        if approve:
            s.stage_action(stage,self.workspace,approve=result['artifact_sha256'],reviewer='TEST ONLY',
                           evidence='Synthetic test approval; not a real user review')
        return result

    def through(self, last):
        result = None
        for stage in s.registry()['stages']:
            result = self.submit(stage['command'])
            if stage['command'] == last: break
        return result

    def test_six_stages_have_different_skills_and_clear_legacy_owners(self):
        routes = [s.skill_route(x['command']) for x in s.registry()['stages']]
        self.assertEqual(len({r['skill'] for r in routes}),6)
        self.assertTrue(all(r['host_must_load_skill'] and not r['cli_invokes_language_model'] for r in routes))
        self.assertEqual(s.skill_route('build')['skill'],'ppt-compose')
        self.assertEqual(s.skill_route('qa')['skill'],'ppt-review')

    def test_empty_command_routes_without_claiming_it_performed_skill_work(self):
        result = s.stage_action('intake',self.workspace)
        self.assertEqual(result['status'],'needs_skill_execution')
        self.assertFalse(self.workspace.exists())

    def test_missing_required_inputs_block_approval(self):
        payload = {**self.requirements,'audience':''}
        result = self.submit('intake',payload,approve=False)
        self.assertEqual(result['status'],'needs_input')
        with self.assertRaises(WorkflowError):
            s.stage_action('intake',self.workspace,approve=result['artifact_sha256'],reviewer='TEST',evidence='TEST')

    def test_required_unanswered_question_is_not_silently_assumed(self):
        payload = {**self.requirements,'open_questions':[{'question':'实际受众是谁？','required':True,'answer':None}]}
        result = self.submit('intake',payload,approve=False)
        self.assertEqual(result['status'],'needs_input')

    def test_optional_question_does_not_block_submission(self):
        payload = {**self.requirements,'open_questions':[{'question':'有偏爱的插画吗？','required':False,'answer':None}]}
        self.assertEqual(self.submit('intake',payload,approve=False)['status'],'needs_review')

    def test_unapproved_requirements_block_outline(self):
        self.submit('intake',approve=False)
        with self.assertRaisesRegex(WorkflowError,'human approval'):
            self.submit('outline')

    def test_wrong_hash_cannot_approve_current_version(self):
        self.submit('intake',approve=False)
        with self.assertRaises(WorkflowError):
            s.stage_action('intake',self.workspace,approve='0'*64,reviewer='TEST',evidence='TEST')

    def test_full_chain_preserves_unverified_review_as_nonrelease(self):
        self.through('review')
        doc, checksum = s._verify(self.workspace,'review')
        result = s.stage_action('review',self.workspace,approve=checksum,reviewer='TEST',evidence='TEST')
        self.assertFalse(result['release_allowed'])
        self.assertEqual(doc['payload']['decision'],'unverified')

    def test_new_upstream_version_invalidates_all_downstream(self):
        self.through('template')
        self.submit('intake',{**self.requirements,'goal':'修改后的试点目标'})
        with self.assertRaisesRegex(WorkflowError,'stale'):
            s._verify(self.workspace,'template')

    def test_source_attachment_change_invalidates_outline(self):
        self.submit('intake')
        source = self.base/'source.json';write(source,{'note':'first'})
        payload = deepcopy(self.outline)
        payload['sources'][1]['locator'] = str(source)
        self.submit('outline',payload)
        write(source,{'note':'changed'})
        with self.assertRaisesRegex(WorkflowError,'attachment changed'):
            s._verify(self.workspace,'outline')

    def test_changing_payload_cannot_reuse_approval(self):
        result = self.submit('intake')
        path = Path(result['artifact'])
        doc = read(path);doc['payload']['goal']='tampered';write(path,doc)
        with self.assertRaisesRegex(WorkflowError,'artifact changed'):
            s._verify(self.workspace,'intake')

    def test_outline_count_must_match_requirements(self):
        self.submit('intake')
        payload = deepcopy(self.outline);payload['slides'].pop()
        with self.assertRaisesRegex(WorkflowError,'page count'):
            self.submit('outline',payload)

    def test_outline_rejects_uncited_fact_or_nonexistent_evidence(self):
        self.submit('intake')
        payload = deepcopy(self.outline);payload['slides'][0]['evidence_refs']=['nonexistent']
        with self.assertRaisesRegex(WorkflowError,'evidence'):
            self.submit('outline',payload)

    def test_outline_rejects_changed_demo_values(self):
        self.submit('intake')
        payload = deepcopy(self.outline);payload['facts'][0]['value']=41
        with self.assertRaisesRegex(WorkflowError,'original record'):
            self.submit('outline',payload)

    def test_template_requires_real_preview(self):
        self.through('outline')
        payload = {**self.template,'preview_paths':[]}
        with self.assertRaisesRegex(WorkflowError,'preview'):
            self.submit('template',payload)

    def test_template_registry_must_match_actual_potx_layouts(self):
        self.through('outline')
        design = read(self.template['design_system']);design['layouts'][0]['name']='Made up layout'
        path = self.base/'design.json';write(path,design)
        with self.assertRaisesRegex(WorkflowError,'absent'):
            self.submit('template',{**self.template,'design_system':str(path)})

    def test_compose_cannot_change_outline_headlines(self):
        self.through('template')
        spec = deepcopy(self.spec);spec['slides'][0]['title']='A different approved claim'
        path=self.base/'spec.json';write(path,spec)
        with self.assertRaisesRegex(WorkflowError,'outline'):
            self.submit('compose',{**self.compose,'deck_spec':str(path)})

    def test_polish_cannot_change_facts(self):
        self.through('compose')
        spec=deepcopy(self.spec);spec['facts'][0]['value']=41
        path=self.base/'polish-spec.json';write(path,spec)
        with self.assertRaisesRegex(WorkflowError,'Polish changed facts'):
            self.submit('polish',{**self.polish,'deck_spec':str(path)})

    def test_compose_cannot_hide_a_different_message_behind_same_title(self):
        self.through('template')
        spec=deepcopy(self.spec);spec['slides'][0]['message']='A different message'
        path=self.base/'different-message.json';write(path,spec)
        with self.assertRaisesRegex(WorkflowError,'main message'):
            self.submit('compose',{**self.compose,'deck_spec':str(path)})

    def test_compose_checks_actual_native_template_instead_of_only_json(self):
        self.through('template')
        presentation=Presentation(self.deck)
        presentation.slides[0].slide_layout.name='Wrong native layout'
        path=self.base/'wrong-template.pptx';presentation.save(path)
        with self.assertRaisesRegex(WorkflowError,'native template'):
            self.submit('compose',{**self.compose,'deck':str(path)})

    def test_polish_can_copyedit_nonfactual_body_without_changing_headlines(self):
        self.through('compose')
        spec=deepcopy(self.spec);element=spec['slides'][0]['elements'][-1];element['text']='试点汇报稿'
        p=Presentation(self.deck)
        next(sh for sh in p.slides[0].shapes if sh.name==element['id']).text=element['text']
        deck=self.base/'copyedited.pptx';p.save(deck)
        path=self.base/'copyedited.json';write(path,spec)
        result=self.submit('polish',{**self.polish,'deck':str(deck),'deck_spec':str(path),
              'changes':[{'element_id':element['id'],'change':'讨论稿改为汇报稿','reason':'正文措辞调整'}]},approve=False)
        self.assertEqual(result['status'],'needs_review')

    def test_polish_can_add_native_decorative_graphics(self):
        self.through('compose')
        spec=deepcopy(self.spec)
        spec['slides'][0]['elements'].append({'id':'decoration-new','type':'shape','role':'decoration','rect':{'x':.8,'y':6.4,'w':.3,'h':.1},
                                             'style':{'fill':'E2EFEB'},'fact_refs':[],'editability_requirement':'native'})
        p=Presentation(self.deck);sh=p.slides[0].shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.8),Inches(6.4),Inches(.3),Inches(.1));sh.name='decoration-new'
        deck=self.base/'decorated.pptx';p.save(deck)
        path=self.base/'decorated.json';write(path,spec)
        result=self.submit('polish',{**self.polish,'deck':str(deck),'deck_spec':str(path),
                 'changes':[{'element_id':'decoration-new','change':'新增可编辑图形','reason':'增强结构提示'}]},approve=False)
        self.assertEqual(result['status'],'needs_review')

    def test_polish_cannot_change_brand_background(self):
        self.through('compose')
        spec=deepcopy(self.spec);spec['slides'][0]['background_color']='000000'
        path=self.base/'brand.json';write(path,spec)
        with self.assertRaisesRegex(WorkflowError,'Brand/background'):
            self.submit('polish',{**self.polish,'deck_spec':str(path)})

    def test_review_cannot_turn_unknown_checks_into_pass(self):
        self.through('polish')
        with self.assertRaisesRegex(WorkflowError,'decision'):
            self.submit('review',{**self.review,'decision':'passed'})

    def test_review_cannot_delete_unknown_from_qa_report(self):
        self.through('polish')
        qa=read(self.review['qa_report']);qa['status']='passed';qa['coverage']['unknown']=[]
        qa['stages']={k:{'status':'passed','evidence':['TEST forged resolution']} for k in qa['stages']}
        path=self.base/'fake-qa.json';write(path,qa)
        with self.assertRaisesRegex(WorkflowError,'silently resolve'):
            self.submit('review',{**self.review,'qa_report':str(path),'decision':'passed'})

    def test_visual_failure_can_be_reported_instead_of_requiring_every_page_pass(self):
        self.through('polish')
        visual=read(self.review['visual_review']);visual['status']='failed';visual['pages'][0].update(status='failed',notes='TEST fixture: title clipping')
        vp=self.base/'visual-failed.json';write(vp,visual)
        qa=read(self.review['automated_qa'])
        qp=self.base/'qa-before-visual.json';write(qp,qa)
        result=self.submit('review',{**self.review,'qa_report':str(qp),'visual_review':str(vp),'decision':'failed'},approve=False)
        self.assertEqual(result['status'],'needs_review')

    def test_individual_and_suite_installation_are_supported(self):
        single=self.base/'single';suite=self.base/'suite'
        for args in (['--dest',str(single),'--skill','ppt-polish','--apply'],['--dest',str(suite),'--apply']):
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),*args],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(len(list(single.glob('*/SKILL.md'))),1)
        self.assertEqual(len(list(suite.glob('*/SKILL.md'))),7)
        self.assertEqual(read(single/'ppt-polish/runtime.json')['project_root'],str(ROOT))

    def test_installer_preflights_suite_without_partially_overwriting(self):
        dest=self.base/'existing';(dest/'ppt-polish').mkdir(parents=True)
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--dest',str(dest),'--apply'],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(proc.returncode,0)
        self.assertFalse((dest/'ppt-intake').exists())


if __name__=='__main__': unittest.main()
