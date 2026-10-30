"""Visual preparation must preserve evidence and native chart data, not invent claims."""
from pathlib import Path
import copy,json,os,shutil,subprocess,tempfile,unittest
from zipfile import ZipFile
from xml.etree import ElementTree as E
from ppt_workflow.chart_style_library import compile_chart_style,number_format,prepare_chart_style,style_catalog
from ppt_workflow.content import inspect_native
from ppt_workflow.chart_preservation import verify_workbook_preservation
ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('PPT_WORKFLOW_NODE') or shutil.which('node') or 'D:/node/node.exe'
class ChartStyleTests(unittest.TestCase):
    def request(self,style='focus-comparison'):return json.loads((ROOT/f'examples/chart-style-{style}.json').read_text(encoding='utf-8'))
    def test_three_explicit_native_styles(self):self.assertEqual(3,len(style_catalog()['styles']))
    def test_unit_is_caption_not_body(self):
        r=compile_chart_style(self.request());unit=next(e for e in r['elements'] if e['id'].endswith('-unit'))
        self.assertEqual(unit['role'],'caption')
    def test_preparation_preserves_categories_values_facts_and_input(self):
        q=self.request();old=copy.deepcopy(q);result=compile_chart_style(q);chart=next(e['chart'] for e in result['elements'] if e['type']=='chart')
        self.assertEqual(old,q)
        for key in ['kind','categories','series','unit','semantics']:self.assertEqual(q['chart'][key],chart[key])
        self.assertEqual(q['facts'],result['facts']);self.assertFalse(result['release_allowed'])
    def test_derived_callout_is_bound_and_percent_difference_unit_preserved(self):
        r=compile_chart_style(self.request());e=next(e for e in r['elements'] if e['id'].endswith('callout-value'))
        self.assertEqual('20百分点',e['text']);self.assertEqual(['bar-gap'],e['fact_refs']);self.assertEqual('{fact:bar-gap}',e['text_template'])
    def test_wrong_formula_or_chart_value_cannot_be_prepared(self):
        q=self.request();next(f for f in q['facts'] if f['id']=='bar-gap')['value']=19
        with self.assertRaises(ValueError):compile_chart_style(q)
        q=self.request();q['chart']['series'][0]['values'][0]=67
        with self.assertRaises(ValueError):compile_chart_style(q)
    def test_callout_cannot_import_an_unrelated_fact(self):
        q=self.request();records=json.loads((ROOT/'examples/chart-demo-source.json').read_text(encoding='utf-8'))['facts'];q['facts'].append(records['col-a-2']);q['callout']['value_template']='{fact:col-a-2}'
        with self.assertRaisesRegex(ValueError,'chart facts'):compile_chart_style(q)
    def test_literal_numeric_claim_and_oversized_annotation_rejected(self):
        q=self.request();q['callout']['body_template']='增长30%'
        with self.assertRaisesRegex(ValueError,'fact templates'):compile_chart_style(q)
        q=self.request();q['callout']['body_template']='过长说明'*30
        with self.assertRaisesRegex(ValueError,'capacity'):compile_chart_style(q)
    def test_integer_percentage_labels_have_no_false_precision(self):
        r=compile_chart_style(self.request());chart=next(e['chart'] for e in r['elements'] if e['type']=='chart');self.assertEqual('0"%"',chart['options']['label_format'])
        chart['series'][0]['values'][0]=68.5;self.assertEqual('0.0"%"',number_format(chart))
    def test_high_precision_needs_explicit_format(self):
        c=self.request()['chart'];c['series'][0]['values'][0]=.001
        with self.assertRaisesRegex(ValueError,'label_format'):number_format(c)
    def test_month_order_and_preset_type_are_checked(self):
        q=self.request('focus-trend');q['chart']['categories'].reverse()
        with self.assertRaisesRegex(ValueError,'months'):compile_chart_style(q)
        q=self.request();q['chart']['kind']='column'
        with self.assertRaisesRegex(ValueError,'mismatch'):compile_chart_style(q)
    def test_unknown_tokens_invalid_envelope_and_small_region_fail(self):
        for change in ['token','region','envelope']:
            q=self.request()
            if change=='token':q['callout']['body_template']='{fact:bad.name}'
            elif change=='region':q['rect']['w']=8
            else:q['surprise']=True
            with self.subTest(change=change),self.assertRaises(ValueError):compile_chart_style(q)
    def test_fresh_preparation_has_binding_hashes_and_source_status(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            r=prepare_chart_style(ROOT/'examples/chart-style-focus-comparison.json',Path(t)/'prepared');self.assertEqual(64,len(r['fragment_sha256']));self.assertEqual([],r['source_truth_review'])
            with self.assertRaises(ValueError):prepare_chart_style(ROOT/'examples/chart-style-focus-comparison.json',Path(t)/'prepared')
    def test_native_charts_workbooks_and_display_order_survive_compilation(self):
        requests=[self.request(style) for style in ['focus-comparison','series-comparison','focus-trend']];pages=[];facts=[]
        for i,q in enumerate(requests):
            r=compile_chart_style(q);facts+=q['facts'];pages.append(dict(id=f's{i+1}',title='Synthetic chart',message='TEST',layout='chart_takeaway',background_color='F8F5EE',source_refs=q['source_refs'],notes='Synthetic, not measured',elements=r['elements']))
        spec=dict(schema_version='0.2',job_id='chart-style-test',canvas=requests[0]['canvas'],theme='provided_template',sources=requests[0]['sources'],facts=facts,slides=pages)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            p=Path(t)/'spec.json';p.write_text(json.dumps(spec),encoding='utf-8');deck=Path(t)/'test.pptx'
            proc=subprocess.run([NODE,str(ROOT/'engine/editorial_build.cjs'),str(p),str(deck)],cwd=ROOT,capture_output=True,timeout=25);self.assertEqual(0,proc.returncode,proc.stderr)
            check=inspect_native(deck,spec);self.assertFalse(check.issues,check.issues)
            with ZipFile(deck) as z:
                bar=E.fromstring(z.read('ppt/charts/chart1.xml'));ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
                self.assertEqual('maxMin',bar.find('.//c:catAx/c:scaling/c:orientation',ns).get('val'))
                self.assertEqual('0"%"',bar.find('.//c:dLbls/c:numFmt',ns).get('formatCode'))
                self.assertEqual(3,len([n for n in z.namelist() if n.startswith('ppt/embeddings/') and n.endswith('.xlsx')]))
    def test_unrecognized_line_grouping_is_unverified_not_a_crash_or_pass(self):
        q=self.request('focus-trend');r=compile_chart_style(q)
        spec=dict(schema_version='0.2',job_id='line-grouping-test',canvas=q['canvas'],theme='provided_template',sources=q['sources'],facts=q['facts'],slides=[dict(id=q['slide_id'],title='Synthetic',message='TEST',layout='chart_takeaway',background_color='F8F5EE',source_refs=q['source_refs'],notes='Synthetic',elements=r['elements'])])
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            p=Path(t)/'spec.json';p.write_text(json.dumps(spec),encoding='utf-8');deck=Path(t)/'original.pptx'
            proc=subprocess.run([NODE,str(ROOT/'engine/editorial_build.cjs'),str(p),str(deck)],cwd=ROOT,capture_output=True,timeout=25);self.assertEqual(0,proc.returncode,proc.stderr)
            changed=Path(t)/'grouping-variant.pptx'
            with ZipFile(deck) as src,ZipFile(changed,'w') as dst:
                for name in src.namelist():
                    data=src.read(name)
                    if name=='ppt/charts/chart1.xml':
                        root=E.fromstring(data);ns='{http://schemas.openxmlformats.org/drawingml/2006/chart}';plot=root.find('.//'+ns+'lineChart');self.assertIsNotNone(plot);group=plot.find(ns+'grouping')
                        if group is None:group=E.SubElement(plot,ns+'grouping')
                        group.set('val','none');data=E.tostring(root)
                    dst.writestr(name,data)
            check=inspect_native(changed,spec);self.assertEqual('unverified',check.status);self.assertTrue(any('type-unrecognized' in v for v in check.unknown));self.assertFalse(check.issues);self.assertEqual(1,len(check.details['charts']))
    def test_wps_copy_with_visible_cache_but_lost_workbook_is_blocked(self):
        q=self.request();r=compile_chart_style(q);spec=dict(schema_version='0.2',job_id='workbook-loss-test',canvas=q['canvas'],theme='provided_template',sources=q['sources'],facts=q['facts'],slides=[dict(id=q['slide_id'],title='Synthetic',message='TEST',layout='chart_takeaway',background_color='F8F5EE',source_refs=q['source_refs'],notes='Synthetic',elements=r['elements'])])
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as t:
            p=Path(t)/'spec.json';p.write_text(json.dumps(spec),encoding='utf-8');deck=Path(t)/'source.pptx';bad=Path(t)/'lost-workbook.pptx'
            proc=subprocess.run([NODE,str(ROOT/'engine/editorial_build.cjs'),str(p),str(deck)],cwd=ROOT,capture_output=True,timeout=25);self.assertEqual(0,proc.returncode,proc.stderr)
            good=verify_workbook_preservation(deck,deck,[1]);self.assertEqual('passed',good['status']);self.assertEqual(1,len(good['checked']))
            with ZipFile(deck) as src,ZipFile(bad,'w') as dst:
                for name in src.namelist():
                    if name.startswith('ppt/embeddings/'):continue
                    dst.writestr(name,src.read(name))
            failed=verify_workbook_preservation(deck,bad,[1]);self.assertEqual('failed',failed['status']);self.assertEqual('embedded-chart-workbook-lost',failed['issues'][0]['rule']);self.assertEqual('failed',inspect_native(bad,spec).status)

if __name__=='__main__':unittest.main()
