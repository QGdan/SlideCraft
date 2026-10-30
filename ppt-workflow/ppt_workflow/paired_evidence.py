"""Compact native comparison for a deliberate image + chart composition."""
from copy import deepcopy
import math,re
from .online_assets import ROOT,local,fresh,read,write
from .contracts import validate
from .charts import validate_chart
from .content import check_ledger
from .textflow import wrap_native
from .chart_style_library import number_format

IMAGE_SLOT=dict(x=.75,y=2.95,w=4.8,h=3.35)
CHART_SLOT=dict(x=6.05,y=2.95,w=6.55,h=3.35)

def compile_compact_chart(q):
    fields={'version','slide_id','element_id','theme','chart','sources','facts','source_refs','heading','source_note'}
    if not isinstance(q,dict) or set(q)!=fields or q['version']!='compact-chart-request/1':raise ValueError('Exact compact-chart-request/1 fields required')
    for key in ('slide_id','element_id'):
        if not isinstance(q[key],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}',q[key]):raise ValueError('Stable compact chart IDs required')
    theme=q['theme']
    if not isinstance(theme,dict) or set(theme)!={'font','colors'} or theme['font']!='Microsoft YaHei':raise ValueError('Compact chart uses measured Microsoft YaHei')
    colors=theme['colors']
    if not isinstance(colors,dict) or not all(isinstance(colors.get(k),str) and re.fullmatch('[A-Fa-f0-9]{6}',colors[k]) for k in ('ink','accent','muted','secondary','background')):raise ValueError('Compact chart role colors required')
    if not all(isinstance(q[k],str) and q[k].strip() for k in ('heading','source_note')):raise ValueError('Actual heading and source note required')
    chart=deepcopy(q['chart'])
    if not isinstance(chart,dict) or chart.get('kind')!='bar' or not 2<=len(chart.get('categories',[]))<=4 or len(chart.get('series',[]))!=1:raise ValueError('Compact comparison supports one bar series and 2–4 categories')
    if any(not isinstance(c,str) or len(c)>8 for c in chart['categories']):raise ValueError('Short compact category labels required')
    values=chart['series'][0]['values']
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):raise ValueError('Compact comparison needs finite nonnegative values')
    options=chart.setdefault('options',{})
    if not isinstance(options,dict):raise ValueError('Compact chart options must be an object')
    # Keep the original facts/order/labels; only theme and presentation are applied.
    if 'label_format' not in options:options['label_format']=number_format(chart)
    options.update(presentation_preset='focus-comparison',font_face=theme['font'],colors=dict(ink=colors['ink'],accent=colors['accent'],muted=colors['secondary'],series=[colors['accent']]))
    refs=list(dict.fromkeys(chart['series'][0].get('fact_ids',[])));eid=q['element_id']
    heading,hh=wrap_native(q['heading'],6.55,18,True,max_lines=1)
    note=('示意数据，非实测。' if any(s.get('is_demo') for s in q['sources'] if s['id'] in q['source_refs']) else '')+q['source_note']
    note,nh=wrap_native(note,6.55,10,max_lines=2)
    elements=[dict(id=eid+'-heading',type='text',role='caption',rect=dict(x=6.05,y=2.38,w=6.55,h=max(.42,hh)),text=heading,editability_requirement='native',fact_refs=[],style=dict(font_face=theme['font'],font_size_pt=18,color=colors['ink'],bold=True)),dict(id=eid+'-chart',type='chart',role='data',rect=deepcopy(CHART_SLOT),chart=chart,editability_requirement='native',fact_refs=refs),dict(id=eid+'-source',type='text',role='source',rect=dict(x=6.05,y=6.55,w=6.55,h=max(.44,nh)),text=note,editability_requirement='native',fact_refs=[],style=dict(font_face=theme['font'],font_size_pt=10,color=colors['muted']))]
    spec=dict(schema_version='0.2',job_id='compact-native-chart',canvas=dict(width=13.333,height=7.5,unit='in'),theme='provided_template',sources=q['sources'],facts=q['facts'],slides=[dict(id=q['slide_id'],title=q['heading'],message=q['heading'],layout='image-chart',background_color=colors['background'],notes='Prepared compact chart source',source_refs=q['source_refs'],elements=elements)])
    errors=validate(spec,'deck')
    if not errors:errors=validate_chart(chart,'0.2')
    if errors:raise ValueError('Invalid compact chart: '+str(errors[:3]))
    ledger=check_ledger(spec,ROOT)
    if ledger.issues:raise ValueError('Compact chart fact/source mismatch: '+str(ledger.issues[:3]))
    return dict(version='compact-chart-fragment/1',slide_id=q['slide_id'],source_refs=deepcopy(q['source_refs']),sources=deepcopy(q['sources']),facts=deepcopy(q['facts']),chart=chart,elements=elements,editability='native chart with fact IDs and source; image prepared separately')

def prepare_compact_chart(input_path,out):
    result=compile_compact_chart(read(local(input_path)));out=fresh(out);out.mkdir(parents=True);write(out/'elements.json',result)
    return dict(status='prepared',fragment=str(out/'elements.json'))
