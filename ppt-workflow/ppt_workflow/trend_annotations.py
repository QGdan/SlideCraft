"""Native fact-bound note strip above an existing native trend chart.

Category labels identify observations; no invented chart-point pixel coordinates.
"""
from copy import deepcopy
import re
from .online_assets import local,fresh,read,write
from .chart_style_library import compile_chart_style
from .design import render_template
from .textflow import measure_lines

def compile_trend(q):
    if not isinstance(q,dict) or set(q)!={'version','chart_request','annotations'} or q['version']!='trend-annotation-request/1':raise ValueError('Exact trend-annotation-request/1 fields required')
    request=deepcopy(q['chart_request']);annotations=q['annotations']
    if request.get('style_id')!='focus-trend':raise ValueError('Annotations currently require native focus-trend')
    fragment=compile_chart_style(request)
    if not isinstance(annotations,list) or not 1<=len(annotations)<=2:raise ValueError('One or two category annotations required')
    facts={f['id']:f for f in request['facts']};chart=request['chart'];categories=chart['categories'];seen=set();r=request['rect'];colors=request['theme']['colors'];eid=request['element_id']
    if request['theme']['font']!='Microsoft YaHei':raise ValueError('Measured annotation strip uses Microsoft YaHei')
    width=(r['w']*.68-.35)/2
    elements=[]
    for i,a in enumerate(annotations):
        if not isinstance(a,dict) or set(a)!={'category','text_template'} or a['category'] not in categories or a['category'] in seen:raise ValueError('Distinct existing category and fact template required')
        seen.add(a['category']);index=categories.index(a['category']);template=a['text_template']
        if not isinstance(template,str) or not template.strip():raise ValueError('Nonempty annotation template required')
        refs=re.findall(r'\{fact:([A-Za-z0-9_-]+)\}',template);remaining=re.sub(r'\{fact:[A-Za-z0-9_-]+\}','',template)
        permitted={s['fact_ids'][index] for s in chart['series']}
        if not refs or not set(refs)<=permitted or '{fact:' in remaining or re.search(r'\d',remaining):raise ValueError('Annotation numbers must bind this category chart facts')
        value=render_template(template,facts)
        if len(measure_lines(value,width,17))>1:raise ValueError('Short one-line annotation needed; keep long explanation on another page')
        x=r['x']+i*(width+.35)
        category_label=a['category']+((' · 单位：'+chart['unit']) if i==0 else '')
        for suffix,text,y,h,size,color,role in [('category',category_label,r['y']-.02,.26,12,colors['muted'],'caption'),('note',value,r['y']+.28,.4,17,colors['ink'],'data')]:
            e=dict(id=f'{eid}-anno{i}-{suffix}',type='text',role=role,rect=dict(x=x,y=y,w=width,h=h),text=text,editability_requirement='native',fact_refs=[],style=dict(font_face=request['theme']['font'],font_size_pt=size,color=color,bold=suffix=='note'))
            if suffix=='note':e.update(text_template=template,fact_refs=list(dict.fromkeys(refs)))
            elements.append(e)
    native=next(e for e in fragment['elements'] if e['type']=='chart');native['rect']['y']+=.65;native['rect']['h']-=.65
    fragment['elements']=[e for e in fragment['elements'] if not e['id'].endswith('-unit')]+elements
    fragment.update(version='trend-annotation-fragment/1',annotations=deepcopy(annotations),annotation_geometry='Native notes above chart with explicit categories; no chart-point pixel mapping')
    return fragment

def prepare_trend(input_path,out):
    result=compile_trend(read(local(input_path)));out=fresh(out);out.mkdir(parents=True);write(out/'elements.json',result)
    return dict(status='prepared',fragment=str(out/'elements.json'),annotations=len(result['annotations']))
