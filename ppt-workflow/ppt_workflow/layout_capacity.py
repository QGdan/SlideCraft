"""Original content-first allocation recipes for the existing editorial compiler.

No inferred facts or hidden summarisation. Layout choice is a small, explained
capacity comparison. Images/charts are bound later by existing material tools.
"""
from copy import deepcopy
import math,re
from .textflow import measure_lines,line_height
from .online_assets import fresh,read,write,local

COLORS=dict(ink='183341',accent='9B3045',muted='657783',background='F8F5EE',surface='EDE5DF',line='A6B2B6')
RECIPES={
 'text-wide':dict(evidence='none',description='单栏顺序阅读，适合连续解释',columns=[dict(x=.75,w=11.85)]),
 'text-columns':dict(evidence='none',description='先左后右的双栏，适合较长的分节正文',columns=[dict(x=.75,w=5.65),dict(x=6.95,w=5.65)]),
 'image-led':dict(evidence='image',description='图片占主导，短文解释画面证据',columns=[dict(x=8,w=4.6)],evidence_rect=dict(x=.75,y=2.12,w=6.75,h=4.55)),
 'image-balanced':dict(evidence='image',description='增加文字宽度，保留完整图片证据区',columns=[dict(x=6.65,w=5.95)],evidence_rect=dict(x=.75,y=2.12,w=5.4,h=4.55)),
 'image-right':dict(evidence='image',description='左侧正文，右侧主图；按素材主体选择裁切',columns=[dict(x=.75,w=5.35)],evidence_rect=dict(x=6.65,y=2.12,w=5.95,h=4.55)),
 'image-story':dict(evidence='image',description='上图下文，两组短说明引导观察与解释',columns=[dict(x=.75,w=5.65,y=5.3),dict(x=6.95,w=5.65,y=5.3)],evidence_rect=dict(x=.75,y=2.12,w=11.85,h=2.9)),
 'chart-focus':dict(evidence='chart',description='为已有原生图表与事实结论配方保留完整区域',columns=[],evidence_rect=dict(x=.75,y=2.3,w=11.85,h=4.3)),
}

def rect(x,y,w,h):return dict(x=x,y=y,w=w,h=h)

def validate_request(q):
    allowed={'version','slide_id','title','kicker','source_note','blocks','evidence','layout','page_limit','colors'}
    if not isinstance(q,dict) or set(q)-allowed or q.get('version')!='layout-request/1':raise ValueError('layout-request/1 required; unknown fields are not accepted')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,17}',q.get('slide_id','')):raise ValueError('Stable slide ID of at most 18 characters required')
    for k in ('title','kicker','source_note'):
        if not isinstance(q.get(k),str) or not q[k].strip():raise ValueError(f'{k}: nonempty actual copy required')
    if q.get('evidence') not in ('none','image','chart'):raise ValueError('Explicit evidence: none, image or chart required')
    blocks=q.get('blocks')
    if not isinstance(blocks,list) or len(blocks)>40:raise ValueError('Up to 40 ordered body blocks required')
    ids=[]
    for b in blocks:
        if not isinstance(b,dict) or set(b)!={'id','heading','text'} or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,15}',b.get('id','')):raise ValueError('Each block needs id, heading and text')
        if not all(isinstance(b[k],str) and b[k].strip() for k in ('heading','text')):raise ValueError('Actual heading and body copy required')
        ids.append(b['id'])
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate body block ID')
    if q['evidence']=='none' and not blocks:raise ValueError('Text layout needs body content')
    if q['evidence']=='chart' and blocks:raise ValueError('Chart recipe reserves its region for native chart and fact-bound callout; put long explanation on a separate page')
    if 'page_limit' in q and (type(q['page_limit']) is not int or not 1<=q['page_limit']<=100):raise ValueError('page_limit must be 1–100')
    if q.get('layout') and q['layout'] not in RECIPES:raise ValueError('Unknown supported layout')
    if 'colors' in q and (set(q['colors'])!=set(COLORS) or not all(re.fullmatch('[0-9A-Fa-f]{6}',c) for c in q['colors'].values())):raise ValueError('Supply all six role colors as hex values')
    return q

def allocate(q,key):
    r=RECIPES[key]
    if r['evidence']!=q['evidence']:raise ValueError('Layout does not match declared evidence type')
    # Reserve title, footer and source before allocating the main region.
    title=measure_lines(q['title'],11.85,30,True)
    if len(title)>2:raise ValueError('Title exceeds two lines; rewrite title before layout')
    top=max(2.12,1.0+len(title)*line_height(30)+.22);bottom=6.67
    source=measure_lines(q['source_note'],11.1,10)
    if len(source)>2:raise ValueError('Source note exceeds two footer lines')
    pages=[dict(parts=[])];col=0;y=top
    if q['evidence']=='chart':
        if len(title)>1:raise ValueError('Chart-focus needs a one-line title or a different chart region')
        return dict(pages=pages,top=top,title_lines=title,source_lines=source)
    columns=r['columns']
    y=columns[0].get('y',top)
    for b in q['blocks']:
        offset=0;continuation=False
        while offset<len(b['text']):
            region=columns[col];w=region['w']
            heading=b['heading']+('（续）' if continuation else '')
            hl=measure_lines(heading,w,20,True)
            if len(hl)>2:raise ValueError('Body heading exceeds two lines')
            hh=len(hl)*line_height(20)+.05
            lines=measure_lines(b['text'][offset:],w,19)
            slots=math.floor((bottom-y-hh-.15-.06)/line_height(19))
            # Avoid a stranded heading or a lone first line at the column bottom.
            if slots<min(2,len(lines)):
                col+=1
                if col==len(columns):col=0;pages.append(dict(parts=[]))
                y=columns[col].get('y',top)
                continue
            count=min(slots,len(lines));chunk=lines[:count];end=offset+chunk[-1]['end'];bh=count*line_height(19)+.06
            absolute_lines=[{**line,'start':offset+line['start'],'end':offset+line['end']} for line in chunk]
            pages[-1]['parts'].append(dict(block_id=b['id'],source_start=offset,source_end=end,source_text=b['text'][offset:end],heading=heading,heading_lines=hl,body_lines=absolute_lines,heading_rect=rect(region['x'],y,w,hh),body_rect=rect(region['x'],y+hh+.1,w,bh)))
            y+=hh+.1+bh+.28;offset=end;continuation=True
            if len(pages)>100:raise ValueError('Content exceeds 100 pages; divide the task')
    return dict(pages=pages,top=top,title_lines=title,source_lines=source)

def plan_layout(q):
    validate_request(q);candidates=[];allocations={};rejected=[]
    for key,r in RECIPES.items():
        if r['evidence']!=q['evidence']:continue
        try:
            a=allocate(q,key);allocations[key]=a
            candidates.append(dict(layout=key,page_count=len(a['pages']),reason=r['description']))
        except ValueError as exc:rejected.append(dict(layout=key,reason=str(exc)))
    if not candidates:raise ValueError('No supported layout fits: '+str(rejected))
    # The rule is visible: fewer pages first, then readable continuous copy.
    preferred='text-columns' if sum(len(b['text']) for b in q['blocks'])>420 and len(q['blocks'])>=2 else 'text-wide'
    if q['evidence']=='image':preferred='image-led'
    candidates.sort(key=lambda x:(x['page_count'],x['layout']!=preferred))
    chosen=q.get('layout') or candidates[0]['layout']
    if chosen not in allocations:raise ValueError('Requested layout is incompatible or exceeds capacity: '+str(rejected))
    allocation=allocations[chosen];n=len(allocation['pages'])
    blocked=q.get('page_limit',100)<n
    result=dict(version='layout-plan/1',status='needs_input' if blocked else 'planned',selected_layout=chosen,selection_reason='先比较实际文字测量后的页数；同页数按阅读长度与图片证据面积选择。显式指定版式时优先使用指定版式。',candidates=candidates,rejected_candidates=rejected,page_count=n,page_limit=q.get('page_limit'),font='Microsoft YaHei',font_sizes=dict(title=30,heading=20,body=19,source=10),source_request=deepcopy(q),pages=[],editability='native_text; evidence bound by existing asset/chart tools')
    if blocked:result['action']='页数已锁定：保留原文，调整页数或由作者明确改写后重排；尚未生成制作片段。'
    for i,page in enumerate(allocation['pages'],1):
        page.update(id=f"{q['slide_id']}-p{i}",title=q['title'],title_rect=rect(.75,1.0,11.85,len(allocation['title_lines'])*line_height(30)+.06),title_lines=allocation['title_lines'],source_lines=allocation['source_lines'],evidence_rect=deepcopy(RECIPES[chosen].get('evidence_rect')))
        # Taller title moves the evidence down too, preserving footer space.
        if page['evidence_rect'] and q['evidence']=='image':page['evidence_rect'].update(y=allocation['top'],h=(5.02 if chosen=='image-story' else 6.67)-allocation['top'])
        result['pages'].append(page)
    # Assert losslessness independently of inserted line breaks.
    for b in q['blocks']:
        parts=[p for page in result['pages'] for p in page['parts'] if p['block_id']==b['id']]
        assert ''.join(p['source_text'] for p in parts)==b['text']
    return result

def compile_pages(plan):
    if plan['status']!='planned':raise ValueError('Page limit needs author decision before composing')
    q=plan['source_request'];colors=q.get('colors',COLORS);out=[]
    for n,page in enumerate(plan['pages'],1):
        elements=[];sid=page['id']
        def text(key,value,r,size,color='ink',bold=False,role='body'):
            elements.append(dict(id=sid+'-'+key,type='text',role=role,rect=r,text=value,fact_refs=[],editability_requirement='native',style=dict(font_face='Microsoft YaHei',font_size_pt=size,color=colors[color],bold=bold)))
        text('kicker',q['kicker'],rect(.75,.42,11.85,.28),11,'accent',role='caption')
        # Kicker is small but still measured rather than silently overflowing.
        if len(measure_lines(q['kicker'],11.85,11))>1:raise ValueError('Kicker must fit one line')
        text('title','\n'.join(x['text'] for x in page['title_lines']),page['title_rect'],30,bold=True,role='title')
        for i,p in enumerate(page['parts']):
            text(f'h{i}','\n'.join(x['text'] for x in p['heading_lines']),p['heading_rect'],20,'accent',True)
            text(f'b{i}','\n'.join(x['text'] for x in p['body_lines']),p['body_rect'],19)
        # The existing chart fragment carries its own demo/source statement.
        if q['evidence']!='chart':text('source','\n'.join(x['text'] for x in page['source_lines']),rect(.75,6.97,11.1,.4),10,'muted',role='source')
        text('page',f'{n:02}',rect(12.1,7.02,.5,.25),10,'accent',role='source')
        out.append(dict(id=sid,title=q['title'],message=q['title'],layout=plan['selected_layout'],background_color=colors['background'],notes='Layout source copy and spans are retained in layout-plan.json. Evidence supplied separately.',source_refs=[],elements=elements))
    return dict(version='page-fragment/1',selected_layout=plan['selected_layout'],slides=out,evidence_slots=[dict(slide_id=p['id'],rect=p['evidence_rect']) for p in plan['pages'] if p['evidence_rect']])

def prepare_layout(input_path,out,compose=False):
    q=read(local(input_path));plan=plan_layout(q);fragment=compile_pages(plan) if compose and plan['status']=='planned' else None
    out=fresh(out);out.mkdir(parents=True,exist_ok=False);write(out/'layout-plan.json',plan)
    if fragment:write(out/'pages.json',fragment)
    return dict(status=plan['status'],selected_layout=plan['selected_layout'],page_count=plan['page_count'],plan=str(out/'layout-plan.json'),**({'fragment':str(out/'pages.json')} if fragment else {}))

def capacity_catalog():
    from .online_assets import ROOT
    result=[]
    for p in sorted((ROOT/'templates').glob('*/index.json')):
        index=read(p)
        if index.get('version')!='capacity-template/1':continue
        result.append({**index,'path':str(p),'available':all((ROOT/x['preview']).is_file() for x in index['representatives'])})
    return result
