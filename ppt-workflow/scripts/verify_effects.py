"""Create a clearly labelled engineering pilot with real-case and synthetic pages.

Does not register business approvals or overwrite an existing output.
"""
from pathlib import Path
import argparse,json,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ppt_workflow.exhibits import compose_exhibit
from ppt_workflow.content import inspect_native,check_ledger
from ppt_workflow.contracts import validate

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--node',required=True);a=p.parse_args()
out=a.out.resolve()
if not out.is_relative_to(ROOT/'runs') or out.exists():raise SystemExit('Fresh output inside runs required')
out.mkdir(parents=True)
palette={'accent':'8C2633','muted':'9CA7AF','ink':'183247'}
theme={'font':'Microsoft YaHei','colors':{**palette,'muted':'5E6B75'}}
source='https://zqb.cyol.com/html/2021-09/13/nw.D110000zgqnb_20210913_1-08.htm'
slides=[]
def text(id,t,x,y,w,h,size=22,bold=False,color=None,role='body',refs=None):
    return dict(id=id,type='text',role=role,rect=dict(x=x,y=y,w=w,h=h),editability_requirement='native',fact_refs=refs or [],text=t,style=dict(font_face=theme['font'],font_size_pt=size,color=color or palette['ink'],bold=bold))
def page(id,title,subtitle,foot):
    if id!='case05':foot+=' 示意，非实测。'
    e=[text(id+'-title',title,.65,.53,12.0,.72,32,True,role='title'),text(id+'-sub',subtitle,.68,1.4,11.9,.55,18,color='5E6B75'),text(id+'-foot',foot,.68,6.91,11.5,.25,11,color='5E6B75',role='source'),text(id+'-number',str(len(slides)+1).zfill(2),12.1,6.88,.5,.3,12,color=palette['accent'])]
    s=dict(id=id,title=title,message=title,layout='chart_takeaway',background_color='FAF8F3',notes='效果验证候选，不是已批准正式成品。\n'+foot,source_refs=['TEST'],elements=e);slides.append(s);return s
def chart(s,id,kind,categories,series,unit,rect,options=None):
    c=dict(kind=kind,categories=categories,series=series,unit=unit,semantics=dict(task='trend' if kind=='line' else 'comparison',category_order='chronological' if kind=='line' else 'unordered',reason='按类别比较或时间变化选择图型'))
    c['options']={'font_face':theme['font'],'colors':palette.copy(),**(options or {})}
    s['elements'].append(dict(id=id,type='chart',role='data',rect=rect,editability_requirement='native',fact_refs=[f for x in series for f in x['fact_ids']],chart=c))

s=page('case05','成长项比高薪项高 26.60 个百分点','2021年公开调查｜首次求职看重的工作属性（摘录）','来源：中国青年报·中青校媒，2021-09-13；回收2700份问卷。不同选项比例不可相加。')
s['notes']+='\n'+source+'\n差值=67.24−40.64；并非统计显著性结论，不能推广为全国总体。'
s['source_refs']=['S1']
chart(s,'case05-chart','bar',['成长与能力提升','工作意义与价值感','高薪与物质基础'],[dict(name='受访者比例',values=[67.24,49.07,40.64],fact_ids=['growth','meaning','salary'])],'%',dict(x=.55,y=2.18,w=8.65,h=3.95),{'emphasize_categories':['成长与能力提升']})
s['elements'] += [text('case05-delta','26.6百分点',9.35,2.72,3.35,.95,33,True,palette['accent'],refs=['delta']),text('case05-unit','成长项与高薪项之差',9.4,3.79,3.0,.45,18,True),text('case05-reading','成长诉求值得关注\n薪资诉求同样合理',9.4,4.65,3.0,1.0,20)]
s['elements'][-3]['text_template']='{fact:delta}'
s=page('case08','休整与失责的区别，在于共同约定','教学情境示例｜同样提出暂停小组任务，可以有不同的行为后果','分析示例，不是调查或访谈发现；不根据一次行为给个人贴标签。')
s['elements']+=compose_exhibit('comparison','case08-compare',[dict(title='说明困难，协商调整',body='交代进度与实际困难\n商定交接和返回安排\n共同确认新的分工'),dict(title='隐瞒进度，直接退出',body='未交接，也未说明风险\n其他成员被迫补位\n原先约定无法履行')],dict(x=.85,y=2.4,w=11.9,h=2.8),theme)
s['elements'].append(text('case08-test','判断依据：是否履行约定，是否把负担转嫁给他人',.85,5.8,11.9,.65,24,True))
s=page('case11','把劳动落实为一份可用的报修指引','建议任务｜尚未实施；按所在学校实际官方流程核对','辛勤：完成核对；诚实：来源与贡献可查；创造：根据实际使用问题修订。')
s['elements']+=compose_exhibit('action','case11-action',[dict(title='核对真实流程',body='查官方渠道\n明确受理范围',output='产出：来源清单'),dict(title='整理操作指引',body='写清入口、步骤\n标明需准备的信息',output='产出：指引初稿'),dict(title='试用并修订',body='记录使用障碍\n逐项核实后改进',output='产出：修订记录'),dict(title='按标准验收',body='流程能操作\n来源与分工可追溯',output='产出：验收清单')],dict(x=.78,y=2.55,w=11.9,h=2.85),theme)

for kind in ('column','line'):
    s=page('test-'+kind,'多系列柱图验证' if kind=='column' else '双系列折线验证','模拟数据｜仅验证编译、样式、渲染和编辑往返','本页为合成测试数据，不代表真实调查或业务结论。')
    categories=['第一期','第二期','第三期','第四期']
    series=[dict(name='甲组',values=[32,46,54,61],fact_ids=[f'{kind}-a{i}' for i in range(4)]),dict(name='乙组',values=[41,40,52,58],fact_ids=[f'{kind}-b{i}' for i in range(4)])]
    chart(s,kind+'-chart',kind,categories,series,'分',dict(x=.9,y=2.05,w=11.5,h=4.45),{'colors':{**palette,'series':['8C2633','385A78']},'show_legend':True,'axis_max':100})

facts=[]
for id,val in [('growth',67.24),('meaning',49.07),('salary',40.64),('delta',26.60)]:
    f=dict(id=id,source_id='S1',value=val,unit='百分点' if id=='delta' else '%',scope='首次求职工作属性',comparison_group='first-job',period='2021',metric=id,locator='工作属性段落',is_demo=False)
    if id=='delta':f['formula']={'op':'subtract','inputs':['growth','salary']}
    facts.append(f)
for s in slides:
    for e in s['elements']:
        if e['type']=='chart' and s['id'].startswith('test-'):
            for ser in e['chart']['series']:
                for id,val in zip(ser['fact_ids'],ser['values']):facts.append(dict(id=id,source_id='TEST',value=val,unit='分',scope=s['id'],period='synthetic',metric=id,locator=id,is_demo=True))
spec=dict(schema_version='0.2',job_id='quality-v1-effect-pilot',canvas=dict(width=13.333333,height=7.5,unit='in'),theme='academic',sources=[dict(id='S1',kind='url',locator=source,is_demo=False),dict(id='TEST',kind='inline',locator='Synthetic fixture',is_demo=True)],facts=facts,slides=slides)
errors=validate(spec,'deck')
if errors:raise ValueError(errors)
(out/'deck-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
deck=out/'效果验证候选.pptx'
r=subprocess.run([a.node,str(ROOT/'engine/editorial_build.cjs'),str(out/'deck-spec.json'),str(deck)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=40)
(out/'build.log').write_text(r.stdout+r.stderr,encoding='utf-8');r.check_returncode()
native=inspect_native(deck,spec);ledger=check_ledger(spec)
record={'deck_sha256':hashlib.sha256(deck.read_bytes()).hexdigest(),'native':native.__dict__,'ledger':ledger.__dict__,'business_approval_registered':False}
(out/'checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
if native.issues or ledger.issues:raise SystemExit(1)
