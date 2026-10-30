"""Fresh-runtime task probes. All records are demo-only, never user stage approvals."""
from pathlib import Path
from copy import deepcopy
import argparse,json,subprocess,sys,time
ORIGINAL=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
ROOT=a.runtime.resolve();sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding='utf-8',errors='replace')
from ppt_workflow.unified import unified_deck,PROFILE
from ppt_workflow.workflow import write,read,sha256
from ppt_workflow.design import render_template,format_fact
from ppt_workflow.content import inspect_native
from ppt_workflow.render import render_deck
OUT=ROOT/'runs/p5-acceptance';OUT.mkdir(exist_ok=a.resume)
frozen={'generator':sha256(ROOT/'engine/editorial_build.cjs'),
    'checker':sha256(ROOT/'ppt_workflow/workflow.py'),'profile':sha256(PROFILE),
    'holdout':'mixed technical case 84/7 minutes, independent of regression values40/1,60/4,0/0',
    'limits':'One synthetic held-out data/text variant in the same template, not evidence of generalization to other templates.'}
if a.resume:
    if read(OUT/'frozen-evaluation.json')!=frozen:raise ValueError('Evaluation rules changed; resume refused')
else:write(OUT/'frozen-evaluation.json',frozen)
records=read(OUT/'results.json') if a.resume else []
def call(argv,log,expected):
    t=time.perf_counter();proc=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=210)
    write(log,{'command':list(map(str,argv)),'exit':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'seconds':time.perf_counter()-t})
    if proc.returncode not in expected:raise RuntimeError(proc.stdout+proc.stderr)
    return proc
for case in ('academic','business','mixed-technical','table-series','existing-ppt-edit'):
    if any(r['case']==case and r['status']=='mechanically-passed' for r in records):continue
    base,_=unified_deck();deck=deepcopy(base);deck['job_id']='p5-'+case
    if case=='table-series':deck['slides']=[deepcopy(base['slides'][7]) for _ in range(8)]
    if case=='academic':titles=['教学报告自动化设计与验证','研究目标与责任边界','同口径的耗时示例','规则汇总与人工判断','耗时差异的示意证据','报告生成与审核方法','四周验证安排','指标与计算口径','研究结论的适用边界','后续验证与答辩讨论']
    elif case=='mixed-technical':titles=['Automation / 自动化试点','Scope / 责任边界','Metrics / 耗时示例','Roles / 汇总分工','Evidence / 原生图表','Workflow / 审核流程','Timeline / 四周安排','Definitions / 指标口径','Review / 试点评估','Decision / 审批事项']
    elif case=='table-series':titles=[f'口径核对表 · 第{i}组' for i in range(1,9)]
    else:titles=[s['title'] for s in deck['slides']]
    for i,(slide,title) in enumerate(zip(deck['slides'],titles),1):
        slide['id']=f's{i:02d}';slide['title']=title;slide['message']=title
        for j,e in enumerate(slide['elements'],1):
            e['id']=f's{i:02d}-e{j:02d}'
            if e['type']=='text' and e['rect']==dict(zip(('x','y','w','h'),read(PROFILE)['regions']['title'])):e['text']=title
            if e['type']=='text' and e['rect']==dict(zip(('x','y','w','h'),read(PROFILE)['regions']['page'])):e['text']=f'{i:02d}'
    if case=='mixed-technical':
        values=[84,7,77,12]
        for slide in deck['slides']:
            for e in slide['elements']:
                if e['type']=='text' and e['role']=='caption':e['text']='Demo · 示意数据'
                if e.get('text')=='覆盖成绩读取、指标统计与初稿生成。\n教学解释与签发由教师完成。':e['text']='Draft automatically.\nReview before release.'
    elif case=='existing-ppt-edit':values=[36,2,34,18]
    else:values=[40,1,39,40]
    for f,v in zip(deck['facts'],values):f['value']=v
    facts={f['id']:f for f in deck['facts']}
    ledger=OUT/f'{case}-ledger.json';write(ledger,{'facts':facts})
    next(s for s in deck['sources'] if s['id']=='demo-report')['locator']=ledger.relative_to(ROOT).as_posix()
    for slide in deck['slides']:
        for e in slide['elements']:
            if e.get('text_template'):e['text']=render_template(e['text_template'],facts)
            if e['type']=='chart':
                for series in e['chart']['series']:series['values']=[facts[k]['value'] for k in series['fact_ids']]
            if e['type']=='table':
                for row,ids in zip(e['table']['rows'],e['table']['fact_ids']):
                    for j,k in enumerate(ids):
                        if k:row[j]=format_fact(facts[k])
    sp=OUT/f'{case}-spec.json';write(sp,deck)
    brief=read(ROOT/'examples/brief.json')|{'job_id':deck['job_id'],'slide_count':len(deck['slides']),
        'theme':deck['theme'],'sources':deck['sources'],'language':'zh-CN-en' if case=='mixed-technical' else 'zh-CN'}
    if case=='table-series':brief['required_native_types']=['text','table']
    bp=OUT/f'{case}-brief.json';write(bp,brief)
    record={'case':case,'demo_only':True,'heldout':case=='mixed-technical','pages':len(deck['slides'])};t=time.perf_counter()
    if case=='existing-ppt-edit':
        folder=OUT/case;folder.mkdir();output=folder/'deck.pptx'
        call(['D:/node/node.exe',ORIGINAL/'experiments/p4/refill.cjs',ORIGINAL/'runs/p4-trials-001/owned-template.pptx',sp,output],folder/'refill.json',{0})
        render=render_deck(output,folder/'render',timeout=90);write(folder/'render-manifest.json',render)
        native=inspect_native(output,deck);write(folder/'native-inspection.json',vars(native))
        record.update(deck=str(output),native_status=native.status,render_status=render['status'],
            rendered_pages=len(render['images']),qa_status='unverified',dependency_scope='P4 isolated automizer, not bundled main runtime')
    else:
        template=ROOT/'templates/unified-v3/Unified-Ivory.potx'
        cp=OUT/f'{case}-config.json'
        write(cp,{'brief':str(bp),'spec':str(sp),'template':str(template),'design_system':str(PROFILE),'node':str(a.node.resolve()),
            'renderer':'powerpoint','design_approval':{'spec_sha256':sha256(sp),'template_sha256':sha256(template),'design_sha256':sha256(PROFILE),
                'reviewer':'agent-functional-probe','evidence':'User authorized P5 synthetic acceptance testing, not approval of new business content.'}})
        run=OUT/case
        call([sys.executable,'-m','ppt_workflow','plan','--config',cp,'--out',run],OUT/f'{case}-plan.json',{0})
        call([sys.executable,'-m','ppt_workflow','build','--run',run,'--with-qa'],OUT/f'{case}-build.json',{2})
        state=read(run/'state.json');qa=read(Path(state['qa_directory'])/'qa.json');render=read(Path(state['qa_directory'])/'render-manifest.json')
        native=inspect_native(run/'rev-000/deck.pptx',deck)
        record.update(deck=str(run/'rev-000/deck.pptx'),native_status=native.status,render_status=render['status'],
            rendered_pages=len(render['images']),qa_status=qa['status'],errors=sum(i['severity']=='error' for i in qa['issues']),
            unknown=len(qa['coverage']['unknown']))
        call([sys.executable,'-m','ppt_workflow','deliver','--run',run,'--out',run/'must-not-release'],OUT/f'{case}-delivery-denied.json',{1})
        if (run/'must-not-release').exists():raise RuntimeError('Unverified delivery incorrectly created output')
    record.update(seconds=round(time.perf_counter()-t,3),sha256=sha256(Path(record['deck'])),status='mechanically-passed' if native.status=='passed' and render['status']=='passed' else 'failed')
    records.append(record);write(OUT/'results.json',records);print(json.dumps(record,ensure_ascii=False),flush=True)
records.append({'case':'real-brand-template','status':'blocked_missing_user_material','reason':'No real academy/brand template supplied; synthetic template does not qualify'})
write(OUT/'results.json',records)
