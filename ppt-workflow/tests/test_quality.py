"""Portable quality contracts: task specificity, truthful uncertainty and routing."""
import copy,json,unittest
from pathlib import Path
from ppt_workflow.quality import validate_content_plan,validate_quality_review,review_decision,review_scaffold,validate_layouts,combine_decisions
from ppt_workflow.contracts import validate
ROOT=Path(__file__).resolve().parents[1]
class QualityTests(unittest.TestCase):
    def setUp(self):
        self.outline=json.loads((ROOT/'examples/quality-outline.json').read_text(encoding='utf-8'))
        self.plan=json.loads((ROOT/'examples/content-plan.json').read_text(encoding='utf-8'))
    def check(self):return validate_content_plan(self.plan,self.outline)
    def test_valid_synthetic_plan(self):self.assertEqual([],self.check())
    def test_repeated_questions_rejected(self):
        self.plan['slides'][0]['quality_checks']=['same','same'];self.assertTrue(self.check())
    def test_nonnumeric_layout_capacity(self):
        d=self.design();d['semantic_layouts']['data']['max_body_characters']=float('nan');self.assertTrue(validate_layouts(d,self.plan))
    def test_unknown_fields_rejected(self):
        self.plan['invented']='x';self.assertTrue(self.check())
    def test_unknown_reference(self):
        self.plan['slides'][0]['evidence_refs'].append('missing');self.assertTrue(self.check())
    def test_claim_drift(self):
        self.plan['slides'][0]['claim']='different';self.assertTrue(self.check())
    def test_page_order(self):
        self.plan['slides'].reverse();self.assertTrue(self.check())
    def test_missing_reasoning(self):
        self.plan['slides'][0]['reasoning']='';self.assertTrue(self.check())
    def test_unlabeled_example(self):
        self.plan['slides'][1]['case']['label']='真实采访';self.assertTrue(self.check())
    def test_missing_case_source(self):
        self.plan['slides'][1]['case']['kind']='source_paraphrase';self.assertTrue(self.check())
    def test_wrong_difference(self):
        self.plan['slides'][0]['derived'][0]['value']=30;self.assertTrue(self.check())
    def test_wrong_percentage_unit(self):
        self.plan['slides'][0]['derived'][0]['unit']='%';self.assertTrue(self.check())
    def test_cross_source_derivation(self):
        self.outline['facts'][1]['source_id']='other';self.assertTrue(self.check())
    def test_zero_denominator(self):
        self.outline['facts'][1]['value']=0;self.plan['slides'][0]['derived'][0]['operation']='divide';self.assertTrue(self.check())
    def test_nonnumeric_derivation(self):
        self.outline['facts'][1]['value']='unmeasured';self.assertTrue(self.check())
    def test_composition_requires_exclusivity(self):
        self.plan['slides'][0]['chart']['task']='composition';self.assertTrue(self.check())
    def test_timing(self):
        self.plan['duration_seconds']=90;self.assertTrue(self.check())
    def report(self):
        report=review_scaffold(self.plan);report['binding']['images']=[{'slide':1,'sha256':'1'*64},{'slide':2,'sha256':'2'*64}]
        return report
    def test_scaffold_is_not_a_pass(self):self.assertEqual('unverified',review_decision(self.report()))
    def test_review_cannot_drop_difficult_questions(self):
        r=self.report();r['checks'].pop();self.assertTrue(validate_quality_review(r,self.plan))
    def test_answer_needs_evidence(self):
        r=self.report();r['checks'][0]['answer']='yes';self.assertTrue(validate_quality_review(r,self.plan))
    def test_negative_answer_fails_even_when_axes_pass(self):
        r=self.report();r['dimensions']={k:{'status':'passed','notes':'TEST'} for k in r['dimensions']};r['checks'][0]['answer']='no'
        self.assertEqual('failed',review_decision(r))
    def test_unresolved_error_cannot_be_averaged_away(self):
        r=self.report();r['findings']=[{'status':'open','severity':'error'}];self.assertEqual('failed',review_decision(r))
    def test_resolved_finding_requires_recheck(self):
        r=self.report();r['findings']=[{'id':'f1','slide_id':'s01','element_id':None,'dimension':'content','severity':'error',
            'owner_stage':'outline','issue':'TEST','evidence':['TEST'],'proposed_fix':'TEST','status':'resolved','resolution_evidence':[]}]
        self.assertTrue(validate_quality_review(r,self.plan))
    def test_quality_cannot_override_automatic_unknown(self):self.assertEqual('unverified',combine_decisions('passed','unverified'))
    def design(self):return {'layouts':[{'key':'data'}],'semantic_layouts':{'data':{'carriers':['native_bar','editable_process'],
        'max_body_characters':60,'max_chart_categories':4,'max_chart_series':2,'min_body_font_pt':18}}}
    def test_semantic_layout_coverage(self):self.assertEqual([],validate_layouts(self.design(),self.plan))
    def test_background_only_is_not_a_quality_template(self):self.assertTrue(validate_layouts({'layouts':[]},self.plan))
    def test_wrong_carrier_rejected(self):
        d=self.design();d['semantic_layouts']['data']['carriers']=['native_line'];self.assertTrue(validate_layouts(d,self.plan))
    def test_capacity_and_minimum_font(self):
        spec={'slides':[{'id':'s01','layout':'data','elements':[{'type':'text','role':'body','text':'x'*80,'style':{'font_size_pt':12}}]}]}
        errors=validate_layouts(self.design(),self.plan,spec);self.assertTrue(any('capacity' in x for x in errors));self.assertTrue(any('font' in x for x in errors))
if __name__=='__main__':unittest.main()
