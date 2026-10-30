"""Prepare fact-bound native charts and adjacent explanation, without inventing claims."""
from pathlib import Path
import copy,hashlib,json,math,re,unicodedata
from decimal import Decimal
from .charts import validate_chart
from .contracts import validate
from .content import check_ledger
from .design import render_template
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'templates/chart-styles/library.json'
def style_catalog():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    if data.get('version')!='chart-styles/1':raise ValueError('Unsupported chart style catalog')
    for row in data['styles']:
        if row.get('preview_path'):
            p=(ROOT/row['preview_path']).resolve()
            if not p.is_relative_to(ROOT/'templates/chart-styles') or hashlib.sha256(p.read_bytes()).hexdigest()!=row['preview_sha256']:raise ValueError('Chart style preview changed')
            row['preview_path']=str(p)
    return dict(status='available',styles=data['styles'],approval='not_implied_by_preview')
def number_format(chart):
    precision=0
    for series in chart['series']:
        for v in series['values']:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('Finite numeric chart data required')
            if float(v).is_integer():continue
            precision=max(precision,max(0,-Decimal(str(v)).as_tuple().exponent))
    if precision>2:raise ValueError('More than two decimal places require an explicit reviewed label_format')
    return '0'+('.'+'0'*precision if precision else '')+('"%"' if chart['unit']=='%' else '')
def compile_chart_style(request):
    fields={'version','style_id','slide_id','element_id','canvas','rect','theme','chart','sources','facts','source_refs','callout','source_note','reason'}
    if not isinstance(request,dict) or set(request)!=fields or request['version']!='chart-style-request/1':raise ValueError('Exact chart-style-request/1 fields required')
    style=next((r for r in style_catalog()['styles'] if r['id']==request['style_id']),None)
    if style is None:raise ValueError('Unknown chart style')
    q=copy.deepcopy(request);r=q['rect'];canvas=q['canvas'];theme=q['theme'];eid=q['element_id']
    for key,maxlen in [('slide_id',63),('element_id',39)]:
        if not isinstance(q[key],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,'+str(maxlen)+'}',q[key]):raise ValueError('Stable slide and element IDs required')
    if not isinstance(q['reason'],str) or not q['reason'].strip():raise ValueError('Selection reason required')
    if not isinstance(r,dict) or set(r)!={'x','y','w','h'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in r.values()):raise ValueError('Finite chart region required')
    if r['x']<0 or r['y']<0 or r['w']<11.4 or r['h']<4.2:raise ValueError('Chart and callout region requires at least 11.4 by 4.2 inches')
    if not isinstance(canvas,dict) or set(canvas)!={'width','height','unit'} or canvas['unit']!='in' or not all(isinstance(canvas[k],(int,float)) and not isinstance(canvas[k],bool) and math.isfinite(canvas[k]) for k in ['width','height']):raise ValueError('Finite inch canvas required')
    if r['x']+r['w']>canvas['width'] or r['y']+r['h']>canvas['height']:raise ValueError('Chart region exceeds canvas')
    if not isinstance(theme,dict) or set(theme)!={'font','colors'} or not isinstance(theme['font'],str) or not theme['font'].strip():raise ValueError('Theme font and colors required')
    colors=theme['colors']
    if not isinstance(colors,dict) or any(not isinstance(colors.get(k),str) or not re.fullmatch('[A-Fa-f0-9]{6}',colors[k]) for k in ['ink','accent','muted','secondary','background']):raise ValueError('Theme role colors required')
    if not isinstance(q['source_note'],str) or not q['source_note'].strip() or len(q['source_note'])>55:raise ValueError('Short source note required')
    if not isinstance(q['chart'],dict):raise ValueError('Chart object required')
    probe=dict(schema_version='0.2',job_id='chart-request-validation',canvas=canvas,theme='provided_template',sources=q['sources'],facts=q['facts'],slides=[dict(id=q['slide_id'],title='图表准备',message='图表输入核对',layout='chart_takeaway',notes=q['reason'],source_refs=q['source_refs'],elements=[dict(id=eid+'-probe',type='chart',role='data',rect=r,editability_requirement='native',fact_refs=[],chart=q['chart'])])])
    errors=validate(probe,'deck')
    if errors:raise ValueError('; '.join(errors))
    chart=q['chart'];options=chart.setdefault('options',{})
    if not isinstance(options,dict):raise ValueError('Chart options object required')
    options.update(presentation_preset=style['id'],font_face=theme['font'],colors=dict(ink=colors['ink'],accent=colors['accent'],muted=colors['secondary'],series=[colors['accent'],colors['secondary']]))
    if 'label_format' not in options:options['label_format']=number_format(chart)
    if any(len(c)>8 for c in chart['categories']) or any(len(s['name'])>8 for s in chart['series']):raise ValueError('Short category and series labels required for these layouts')
    elements=[];facts={f['id']:f for f in q['facts']};refs=[fid for s in chart['series'] for fid in s.get('fact_ids',[])]
    chart_width=r['w']*.68;cx=r['x']+chart_width+.65;cw=r['w']-chart_width-.65
    elements.append(dict(id=eid+'-chart',type='chart',role='data',rect=dict(x=r['x'],y=r['y']+.35,w=chart_width,h=r['h']-.8),editability_requirement='native',fact_refs=list(dict.fromkeys(refs)),chart=chart))
    def add_text(suffix,text,x,y,w,h,size,color,*,bold=False,template=None):
        e=dict(id=eid+'-'+suffix,type='text',role='data' if template else 'body',rect=dict(x=x,y=y,w=w,h=h),editability_requirement='native',fact_refs=[],text=text,style=dict(font_face=theme['font'],font_size_pt=size,color=color,bold=bold))
        if template:
            e['text_template']=template;e['fact_refs']=list(dict.fromkeys(re.findall(r'\{fact:([A-Za-z0-9_-]+)\}',template)))
        elements.append(e);return e
    callout=q['callout']
    if not isinstance(callout,dict) or set(callout)!={'label','value_template','body_template'} or not all(isinstance(v,str) for v in callout.values()):raise ValueError('Callout label/value_template/body_template required')
    if not callout['label'].strip() or len(callout['label'])>12 or '\n' in callout['label']:raise ValueError('Short single-line callout label required')
    match=re.fullmatch(r'\{fact:([A-Za-z0-9_-]+)\}',callout['value_template'])
    if not match:raise ValueError('Callout value must bind one existing fact')
    tokens=re.findall(r'\{fact:([A-Za-z0-9_-]+)\}',callout['value_template']+callout['body_template'])
    if '{fact:' in re.sub(r'\{fact:[A-Za-z0-9_-]+\}','',callout['value_template']+callout['body_template']):raise ValueError('Invalid callout fact token')
    visible=set(refs)
    def grounded(fid,seen=None):
        seen=set() if seen is None else set(seen)
        if fid in seen or fid not in facts:return False
        if fid in visible:return True
        seen.add(fid);formula=facts[fid].get('formula')
        return bool(formula and formula.get('inputs') and all(grounded(v,seen) for v in formula['inputs']))
    if not all(grounded(fid) for fid in tokens):raise ValueError('Callout must refer to chart facts or their declared derivations')
    if re.search(r'\d',re.sub(r'\{fact:[A-Za-z0-9_-]+\}','',callout['body_template'])):raise ValueError('Numeric callout body values must use fact templates')
    value=render_template(callout['value_template'],facts);body=render_template(callout['body_template'],facts)
    width_units=sum(2 if unicodedata.east_asian_width(c) in ['W','F'] else 1 for c in value)
    if width_units>10 or len(body)>32 or body.count('\n')>2:raise ValueError('Callout capacity exceeded; revise the layout or wording')
    unit=add_text('unit','单位：'+chart['unit'],r['x']+.15,r['y'],chart_width,.3,12,colors['muted']);unit['role']='caption'
    add_text('callout-label',callout['label'],cx,r['y']+.4,cw,.6,18,colors['ink'],bold=True)
    add_text('callout-value',value,cx,r['y']+1.15,cw,.9,40,colors['accent'],bold=True,template=callout['value_template'])
    add_text('callout-body',body,cx,r['y']+2.3,cw,1.3,18,colors['muted'],template=callout['body_template'] if tokens and re.search(r'\{fact:',callout['body_template']) else None)
    elements.append(dict(id=eid+'-separator',type='line',role='decoration',rect=dict(x=cx-.3,y=r['y']+.35,w=.01,h=r['h']-.9),editability_requirement='native',fact_refs=[],style=dict(color=colors['secondary'])))
    demo=any(s.get('is_demo') for s in q['sources'] if s.get('id') in q['source_refs'])
    note=('示意数据，非实测。' if demo else '')+q['source_note']
    footer=add_text('source',note,r['x'],r['y']+r['h']-.28,r['w'],.25,11,colors['muted']);footer['role']='source'
    deck=dict(schema_version='0.2',job_id='chart-style-check',canvas=canvas,theme='provided_template',sources=q['sources'],facts=q['facts'],slides=[dict(id=q['slide_id'],title='图表准备',message='绑定事实的图表表达',layout='chart_takeaway',background_color=colors['background'],notes=q['reason'],source_refs=q['source_refs'],elements=elements)])
    errors=validate(deck,'deck')
    if errors:raise ValueError('; '.join(errors))
    errors=validate_chart(chart,'0.2')
    if errors:raise ValueError('; '.join(errors))
    ledger=check_ledger(deck,ROOT)
    if ledger.issues:raise ValueError(json.dumps(ledger.issues,ensure_ascii=False))
    return dict(version='chart-style-fragment/1',style_id=style['id'],slide_id=q['slide_id'],source_refs=q['source_refs'],sources=q['sources'],facts=q['facts'],elements=elements,reason=q['reason'],source_truth_review=ledger.unknown,release_allowed=False)
def prepare_chart_style(input_path,out):
    input_path,out=Path(input_path).resolve(),Path(out).resolve()
    if not input_path.is_relative_to(ROOT) or not input_path.is_file():raise ValueError('Project-local chart style request required')
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh preparation directory inside runs required')
    result=compile_chart_style(json.loads(input_path.read_text(encoding='utf-8')));out.mkdir(parents=True)
    path=out/'elements.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    record=dict(status='prepared',style_id=result['style_id'],fragment=str(path),input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),fragment_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_truth_review=result['source_truth_review'],release_allowed=False)
    (out/'preparation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');return record
