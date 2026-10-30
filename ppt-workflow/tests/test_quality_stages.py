"""Production integration of quality attachments. Synthetic approvals TEST ONLY."""
import copy,json,unittest
from pathlib import Path
import test_stages as stage_fixtures
from unittest.mock import patch
from ppt_workflow import stages
from ppt_workflow.workflow import ROOT,write,read,sha256,WorkflowError
from ppt_workflow.quality import review_scaffold

class QualityStageTests(unittest.TestCase):
    def setUp(self):
        self.case=stage_fixtures.StageTests(methodName='test_empty_command_routes_without_claiming_it_performed_skill_work')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        c=self.case;c.requirements['quality_profile']='quality-v1'
        sample=read(ROOT/'examples/content-plan.json')['slides'][0];pages=[]
        for p in c.outline['slides']:
            q=copy.deepcopy(sample);q.update(id=p['id'],claim=p['takeaway'],evidence_refs=p['evidence_refs'],claim_kind='interpretation',chart=None,derived=[])
            pages.append(q)
        self.plan={'schema_version':'quality-content-plan/1','slides':pages}
        self.plan_path=c.base/'content-plan.json';write(self.plan_path,self.plan);c.outline['quality_plan']=str(self.plan_path)
        d=read(c.template['design_system']);d['semantic_layouts']={l['key']:{'carriers':['native_bar'],'max_body_characters':2000,'max_chart_categories':12,'max_chart_series':4,'min_body_font_pt':12} for l in d['layouts']}
        self.design_path=c.base/'design.json';write(self.design_path,d);c.template['design_system']=str(self.design_path)
    def test_new_profile_cannot_skip_plan(self):
        c=self.case;c.submit('intake');p=copy.deepcopy(c.outline);p.pop('quality_plan')
        with self.assertRaisesRegex(WorkflowError,'quality_plan'):c.submit('outline',p)
    def test_invalid_semantic_plan_blocked(self):
        c=self.case;c.submit('intake');self.plan['slides'][0]['claim']='drift';write(self.plan_path,self.plan)
        with self.assertRaisesRegex(WorkflowError,'claim'):c.submit('outline')
    def test_plan_changes_invalidate_approval(self):
        c=self.case;c.through('outline');self.plan['slides'][0]['reasoning']='changed';write(self.plan_path,self.plan)
        with self.assertRaisesRegex(WorkflowError,'attachment changed'):stages._verify(c.workspace,'outline')
    def test_validator_module_changes_invalidate_approval(self):
        c=self.case;c.through('outline')
        with patch('ppt_workflow.stages._rules_digest',return_value='0'*64),self.assertRaisesRegex(WorkflowError,'contracts changed'):
            stages._verify(c.workspace,'outline')
    def test_missing_semantic_layouts_block_template(self):
        c=self.case;c.through('outline');d=read(self.design_path);d.pop('semantic_layouts');write(self.design_path,d)
        with self.assertRaisesRegex(WorkflowError,'semantic_layouts'):c.submit('template')
    def test_legacy_profile_still_routes_without_quality_plan(self):
        c=self.case;c.requirements.pop('quality_profile');c.outline.pop('quality_plan');self.assertEqual('needs_review',c.through('outline')['status'])
    def test_quality_review_cannot_be_skipped(self):
        c=self.case;c.through('polish')
        with self.assertRaisesRegex(WorkflowError,'quality_review'):c.submit('review')
    def attach_review(self):
        c=self.case;r=review_scaffold(self.plan);r['binding']=read(c.review['visual_review'])['binding']
        path=c.base/'quality-review.json';write(path,r);c.review['quality_review']=str(path)
        return path,r
    def test_full_quality_chain_preserves_unknown(self):
        c=self.case;c.through('polish');self.attach_review();result=c.submit('review',approve=False)
        self.assertEqual('needs_review',result['status']);self.assertEqual('unverified',read(Path(result['artifact']))['payload']['decision'])
    def test_review_binding_must_match_export(self):
        c=self.case;c.through('polish');path,r=self.attach_review();r['binding']['deck_sha256']='0'*64;write(path,r)
        with self.assertRaisesRegex(WorkflowError,'different source/export'):c.submit('review')
    def test_quality_failure_is_not_hidden_by_legacy_decision(self):
        c=self.case;c.through('polish');path,r=self.attach_review();r['checks'][0].update(answer='no',evidence=['TEST ONLY: wrong finding']);write(path,r)
        with self.assertRaisesRegex(WorkflowError,'decision'):c.submit('review')
        c.review['decision']='failed';self.assertEqual('needs_review',c.submit('review',approve=False)['status'])

if __name__=='__main__':unittest.main()
