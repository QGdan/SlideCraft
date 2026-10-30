"""Compile temporary synthetic fixtures; no Office or business PPT authoring."""
import copy,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from ppt_workflow.charts import validate_chart
from ppt_workflow.contracts import validate
from ppt_workflow.content import inspect_native,check_ledger
ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('PPT_WORKFLOW_NODE') or shutil.which('node') or 'D:/node/node.exe'
class ChartCompilerTests(unittest.TestCase):
    def chart(self,kind='bar'):
        return {'kind':kind,'categories':['A','B','C'],'series':[{'name':'Values','values':[60,35,20],'fact_ids':['a','b','c']}],'unit':'%',
            'semantics':{'task':'trend' if kind=='line' else 'comparison','category_order':'chronological' if kind=='line' else 'unordered','reason':'Synthetic regression'}}
    def compile(self,c):
        js="const fs=require('fs');const p=require('pptxgenjs');const {compileChart}=require('./engine/chart_compile.cjs');const q=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(compileChart(new p(),q,{x:1,y:1,w:9,h:4},'chart','FFFFFF','0.2')));"
        return subprocess.run([NODE,'-e',js],input=json.dumps(c),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
    def test_compiler_selects_three_actual_types(self):
        for k in ('bar','column','line'):
            with self.subTest(k=k):
                p=self.compile(self.chart(k));self.assertEqual(0,p.returncode,p.stderr);out=json.loads(p.stdout)
                self.assertEqual('line' if k=='line' else 'bar',out['type']);self.assertEqual('col' if k=='column' else 'bar',out['options']['barDir'])
    def test_axis_cannot_clip(self):
        c=self.chart();c['options']={'axis_max':40};self.assertTrue(validate_chart(c,'0.2'));self.assertNotEqual(0,self.compile(c).returncode)
    def test_numeric_format_has_no_dangling_decimal(self):
        c=self.chart();c['unit']='分';out=json.loads(self.compile(c).stdout)
        self.assertEqual('General',out['options']['dataLabelFormatCode'])
        self.assertEqual('General',out['options']['valAxisLabelFormatCode'])
    def test_multiple_line_series_do_not_stack_value_labels(self):
        c=self.chart('line');c['series'].append({'name':'Other','values':[61,36,21],'fact_ids':['d','e','f']})
        out=json.loads(self.compile(c).stdout);self.assertFalse(out['options']['showValue']);self.assertTrue(out['options']['showLegend'])
        self.assertEqual(2,len(out['data']))
    def test_single_category_emphasis_is_deterministic(self):
        c=self.chart();c['options']={'emphasize_categories':['A']};out=json.loads(self.compile(c).stdout)
        self.assertEqual(['117A7E','ABB8BC','ABB8BC'],out['options']['chartColors'])
        self.assertEqual('0.00"%"',out['options']['dataLabelFormatCode'])
    def test_brand_palette_and_font_are_not_hardcoded(self):
        c=self.chart();c['options']={'emphasize_categories':['A'],'font_face':'Noto Sans','colors':{'accent':'920417','muted':'59616E','ink':'1E2836'}}
        out=json.loads(self.compile(c).stdout);self.assertEqual(['920417','59616E','59616E'],out['options']['chartColors'])
        self.assertEqual('Noto Sans',out['options']['dataLabelFontFace']);self.assertEqual('1E2836',out['options']['dataLabelColor']);self.assertEqual(100,out['options']['valAxisMaxVal'])
    def test_unordered_line_is_rejected(self):
        c=self.chart('line');c['semantics']['category_order']='unordered';self.assertTrue(validate_chart(c,'0.2'));self.assertNotEqual(0,self.compile(c).returncode)
    def test_unsupported_type_never_falls_back(self):
        c=self.chart();c['kind']='scatter';self.assertTrue(validate_chart(c,'0.2'));self.assertNotEqual(0,self.compile(c).returncode)
    def test_unknown_emphasis(self):
        c=self.chart();c['options']={'emphasize_categories':['missing']};self.assertTrue(validate_chart(c,'0.2'))
    def test_capacity(self):
        c=self.chart();c['categories']=[str(i) for i in range(13)];c['series'][0]['values']=[1]*13;self.assertTrue(validate_chart(c,'0.2'))
    def test_legacy_schema_still_reads_original_example(self):
        self.assertEqual([],validate(json.loads((ROOT/'examples/deck.json').read_text(encoding='utf-8')),'deck'))
    def test_native_type_cache_and_workbook_for_three_kinds(self):
        for kind in ('bar','column','line'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
                folder=Path(temp);element={'id':'test-chart','type':'chart','role':'data','rect':{'x':1,'y':1,'w':9,'h':4},'editability_requirement':'native','fact_refs':['a','b','c'],'chart':self.chart(kind)}
                spec={'schema_version':'0.2','job_id':'synthetic-test','canvas':{'width':13.333333,'height':7.5,'unit':'in'},'theme':'business','sources':[],'facts':[],
                    'slides':[{'id':'s01','title':'Synthetic chart','message':'Synthetic','layout':'chart_takeaway','background_color':'FFFFFF','notes':'TEST ONLY','source_refs':[],'elements':[element]}]}
                path=folder/'spec.json';path.write_text(json.dumps(spec),encoding='utf-8');out=folder/'fixture.pptx'
                p=subprocess.run([NODE,str(ROOT/'engine/editorial_build.cjs'),str(path),str(out)],cwd=ROOT,capture_output=True,timeout=25)
                self.assertEqual(0,p.returncode,p.stderr);result=inspect_native(out,spec);self.assertEqual('passed',result.status,result.issues)
                # Same numbers with wrong kind must fail: original silent-bar bug regression.
                element['chart']['kind']='line' if kind!='line' else 'bar'
                self.assertTrue(any(x['rule']=='native-chart-type-mismatch' for x in inspect_native(out,spec).issues))
    def test_percentage_difference_grouping_and_unit(self):
        facts=[]
        for key,value,scope in [('a',60,'Option A'),('b',35,'Option B'),('d',25,'Same question comparison')]:
            facts.append({'id':key,'source_id':'source','value':value,'unit':'百分点' if key=='d' else '%','scope':scope,'comparison_group':'same-question',
                'period':'test','metric':key,'locator':'test/'+key,'is_demo':False})
        facts[2]['formula']={'op':'subtract','inputs':['a','b']}
        deck={'schema_version':'0.2','facts':facts,'sources':[{'id':'source','kind':'inline','is_demo':False}],'slides':[]}
        self.assertFalse(check_ledger(deck).issues)
        facts[2]['unit']='%';self.assertTrue(any(x['rule']=='formula-mismatch' for x in check_ledger(deck).issues))
        facts[2]['unit']='百分点';facts[1]['source_id']='other';self.assertTrue(check_ledger(deck).issues)
if __name__=='__main__':unittest.main()
