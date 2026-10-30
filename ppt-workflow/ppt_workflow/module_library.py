"""Searchable native modules; preview images are not the editable output."""
from pathlib import Path
import copy,hashlib,json,math,re
from datetime import date
from .exhibits import compose_exhibit
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'templates/modules/library.json'
def load_modules():
    d=json.loads(CATALOG.read_text(encoding='utf-8'))
    if d.get('version')!='native-modules/1':raise ValueError('Unsupported module catalog')
    if len({r['id'] for r in d['modules']})!=len(d['modules']):raise ValueError('Duplicate module ID')
    return d
def search_modules(query=''):
    terms=[s for s in re.split(r'[\s,，]+',query.casefold()) if s];rows=[]
    for original in load_modules()['modules']:
        row=copy.deepcopy(original);hay=' '.join([row['id'],row['title'],*row['tags']]).casefold()
        matched=[t for t in terms if t in hay]
        if terms and not matched:continue
        row['matched_terms']=matched;row['editability']='native text and lines'
        if row.get('preview_path'):
            path=(ROOT/row['preview_path']).resolve()
            if not path.is_relative_to(ROOT/'templates/modules') or not path.is_file():raise ValueError('Module preview unavailable')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['preview_sha256']:raise ValueError('Module preview changed')
            row['preview_path']=str(path)
        rows.append(row)
    rows.sort(key=lambda r:(-len(r['matched_terms']),r['id']))
    return dict(status='available',modules=rows,total_matches=len(rows),method='curated native module tag search; not beauty scoring')
def compile_module(request):
    allowed={'version','module_id','element_id','slide_id','rect','theme','items','source_refs','reason'}
    if not isinstance(request,dict) or set(request)!=allowed or request['version']!='module-request/1':raise ValueError('Exact module-request/1 fields required')
    row=next((r for r in load_modules()['modules'] if r['id']==request['module_id']),None)
    if not row:raise ValueError('Unknown module')
    if not isinstance(request['reason'],str) or not request['reason'].strip():raise ValueError('Selection reason required')
    for key,maxlen in [('element_id',39),('slide_id',63)]:
        if not isinstance(request[key],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,'+str(maxlen)+'}',request[key]):raise ValueError('Stable slide/element IDs required')
    refs=request['source_refs']
    if not isinstance(refs,list) or not refs or not all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',v) for v in refs) or len(refs)!=len(set(refs)):raise ValueError('Distinct existing task source_refs required')
    rect=request['rect']
    if not isinstance(rect,dict) or set(rect)!={'x','y','w','h'} or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in rect.values()):raise ValueError('Finite rectangle required')
    if rect['x']<0 or rect['y']<0 or rect['w']<6 or rect['h']<2.8:raise ValueError('Module region too small')
    theme=request['theme']
    if not isinstance(theme,dict) or set(theme)!={'font','colors'} or not isinstance(theme['font'],str) or not theme['font'].strip():raise ValueError('Theme font and colors required')
    if not isinstance(theme['colors'],dict) or not all(k in theme['colors'] and isinstance(theme['colors'][k],str) and re.fullmatch('[0-9A-Fa-f]{6}',theme['colors'][k]) for k in ('ink','accent','muted')):raise ValueError('Theme role colors required')
    items=request['items']
    if not isinstance(items,list) or not row['min_items']<=len(items)<=row['max_items']:raise ValueError('Module item capacity exceeded')
    if rect['w']/len(items)<2.25:raise ValueError('Module columns too narrow')
    kind=row['kind'];eid=request['element_id']
    if kind!='timeline':
        for item in items:
            if not isinstance(item,dict) or not all(isinstance(item.get(k),str) for k in ('title','body')) or not isinstance(item.get('output',''),str):raise ValueError('Title and body required')
            if not item['title'].strip() or not item['body'].strip() or '\n' in item['title'] or item['body'].count('\n')>2 or '\n' in item.get('output',''):raise ValueError('Compact title/body/output line capacity required')
            if len(item['title'])>8 or len(item['body'])>20 or len(item.get('output',''))>9:raise ValueError('Module content capacity exceeded; rewrite or split')
        elements=compose_exhibit(kind,eid,items,rect,theme)
        # Keep title and explanation grouped. Do not stretch a short paragraph
        # across the full region merely because the caller reserved a tall slot.
        for e in elements:
            if e['id'].endswith('-body'):e['rect'].update(y=rect['y']+.7,h=1.05)
            if e['id'].endswith('-title'):e['rect']['h']=.55
            if kind=='comparison' and e['type']=='line':e['rect']['h']=1.95
    else:
        dates=[];elements=[];step=rect['w']/len(items);colors=theme['colors']
        for i,item in enumerate(items):
            if not isinstance(item,dict) or set(item)!={'date','title','body'} or not all(isinstance(v,str) and v.strip() for v in item.values()):raise ValueError('Timeline date/title/body required')
            if not re.fullmatch(r'\d{4}-\d{2}',item['date']):raise ValueError('Timeline requires ISO YYYY-MM dates')
            date.fromisoformat(item['date']+'-01');dates.append(item['date'])
            if len(item['title'])>8 or len(item['body'])>20:raise ValueError('Timeline content capacity exceeded')
            if '\n' in item['title'] or item['body'].count('\n')>2:raise ValueError('Timeline line capacity exceeded')
            x=rect['x']+i*step;w=step-.35
            for suffix,text,y,h,bold,color in [('date',item['date'],rect['y'],.45,False,colors['accent']),('title',item['title'],rect['y']+.95,.6,True,colors['ink']),('body',item['body'],rect['y']+1.65,1.05,False,colors['muted'])]:
                elements.append(dict(id=f'{eid}-n{i+1}-{suffix}',type='text',role='body',rect=dict(x=x,y=y,w=w,h=h),editability_requirement='native',fact_refs=[],text=text,style=dict(font_face=theme['font'],font_size_pt=18,color=color,bold=bold)))
            elements.append(dict(id=f'{eid}-tick{i+1}',type='line',role='diagram',rect=dict(x=x,y=rect['y']+.6,w=.01,h=.18),editability_requirement='native',fact_refs=[],style=dict(color=colors['accent'])))
            if i<len(items)-1:elements.append(dict(id=f'{eid}-axis{i+1}',type='line',role='diagram',rect=dict(x=x,y=rect['y']+.69,w=step,h=.01),editability_requirement='native',fact_refs=[],style=dict(color=colors['accent'])))
        if dates!=sorted(set(dates)):raise ValueError('Timeline dates must be distinct and ascending')
    return dict(version='module-fragment/1',module_id=row['id'],slide_id=request['slide_id'],source_refs=refs,reason=request['reason'],elements=elements,editability='native text and lines; source/semantic approval remains required')
def prepare_module(input_path,out):
    input_path,out=Path(input_path).resolve(),Path(out).resolve()
    if not input_path.is_relative_to(ROOT) or not input_path.is_file():raise ValueError('Project-local module request required')
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh preparation directory inside runs required')
    request=json.loads(input_path.read_text(encoding='utf-8'));result=compile_module(request)
    out.mkdir(parents=True);(out/'request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8');path=out/'elements.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return dict(status='prepared',fragment=str(path),module_id=result['module_id'],element_count=len(result['elements']),release_allowed=False)
