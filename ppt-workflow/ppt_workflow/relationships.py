"""Content relationships compiled into editable scene fragments.

Original implementation informed by the pinned research in folder 23. No upstream
runtime or prompts are copied. Geometry stays here, away from the outline.
"""
from copy import deepcopy
from pathlib import Path
import math,re
from .textflow import wrap_native
from .online_assets import ROOT,local,fresh,read,write

KINDS=('process','hierarchy','comparison')
SHAPES=('rect','roundRect','ellipse','diamond','chevron','hexagon','parallelogram')
ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,23}')

def nonempty(value):return isinstance(value,str) and bool(value.strip())

def validate_relationship(model,sources=None):
    """Validate an asserted relationship, not infer it from superficial keywords."""
    if not isinstance(model,dict) or set(model)-{'kind','basis','source_refs','nodes','edges','dimensions'}:
        raise ValueError('Relationship needs kind, basis, source_refs, nodes and edges')
    kind=model.get('kind');nodes=model.get('nodes');edges=model.get('edges')
    if kind not in KINDS or not nonempty(model.get('basis')):raise ValueError('Supported relationship kind and sourced basis required')
    refs=model.get('source_refs')
    if not isinstance(refs,list) or not refs or len(refs)!=len(set(refs)) or not all(isinstance(x,str) for x in refs):raise ValueError('Distinct source_refs required for relationship')
    if sources is not None and any(x not in sources for x in refs):raise ValueError('Unknown relationship source')
    if not isinstance(nodes,list) or not 2<=len(nodes)<=6:raise ValueError('Relationship supports 2–6 nodes; split or use another structure')
    for n in nodes:
        if not isinstance(n,dict) or set(n)-{'id','label','body','output','cells'} or not ID.fullmatch(n.get('id','')) or not nonempty(n.get('label')):
            raise ValueError('Each node needs a stable short ID and nonempty label')
        if any(k in n and (not isinstance(n[k],str) or not n[k].strip()) for k in ('body','output')):raise ValueError('Node body/output must be nonempty text when supplied')
    ids=[n['id'] for n in nodes]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate relationship node ID')
    if not isinstance(edges,list):raise ValueError('Explicit edges list required')
    pairs=[]
    for e in edges:
        if not isinstance(e,dict) or set(e)-{'from','to','label'} or e.get('from') not in ids or e.get('to') not in ids or e['from']==e['to']:
            raise ValueError('Edge needs different, existing from/to node IDs')
        if 'label' in e and not nonempty(e['label']):raise ValueError('Supplied edge label must be nonempty')
        pairs.append((e['from'],e['to']))
    if len(set(pairs))!=len(pairs):raise ValueError('Duplicate relationship edge')
    if kind=='process':
        if pairs!=list(zip(ids,ids[1:])):raise ValueError('Process edges must match the declared node reading order; branching needs another structure')
    if kind=='hierarchy':
        if len(nodes)>5 or len(edges)!=len(nodes)-1:raise ValueError('Hierarchy currently supports a root and up to four children')
        root=ids[0]
        if set(pairs)!={(root,n) for n in ids[1:]}:raise ValueError('Hierarchy currently supports one explicit root-to-children level')
        if any(e.get('label') for e in edges):raise ValueError('Hierarchy edge labels need a different layout; do not drop them')
        if nodes[0].get('body'):raise ValueError('Root body needs another hierarchy layout; do not place it across relationship lines')
    if kind=='comparison':
        dims=model.get('dimensions')
        if len(nodes)!=2 or edges or not isinstance(dims,list) or not 2<=len(dims)<=4 or not all(nonempty(x) for x in dims) or len(set(dims))!=len(dims):
            raise ValueError('Comparison needs two alternatives, no arrows, and 2–4 distinct shared dimensions')
        if any(set(n.get('cells',{}))!=set(dims) or not all(nonempty(v) for v in n['cells'].values()) for n in nodes):
            raise ValueError('Both alternatives must supply every shared comparison dimension')
        if any('body' in n or 'output' in n for n in nodes):raise ValueError('Comparison prose belongs in cells; no unused body/output')
    elif 'dimensions' in model or any('cells' in n for n in nodes):raise ValueError('Dimensions/cells belong to comparison only')
    return model

def compile_relationship(request):
    allowed={'version','slide_id','element_id','rect','theme','relationship'}
    if not isinstance(request,dict) or set(request)!=allowed or request['version']!='relationship-request/1':raise ValueError('Exact relationship-request/1 fields required')
    model=validate_relationship(request['relationship']);kind=model['kind'];eid=request['element_id']
    if not ID.fullmatch(eid) or not ID.fullmatch(request['slide_id']):raise ValueError('Stable short slide/element IDs required')
    rect=request['rect'];theme=request['theme']
    if not isinstance(rect,dict) or set(rect)!={'x','y','w','h'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in rect.values()):raise ValueError('Finite recipe rectangle required')
    if min(rect['x'],rect['y'])<0 or rect['w']<10 or rect['h']<3.8:raise ValueError('Recipe needs a region at least 10 × 3.8 inches')
    if not isinstance(theme,dict) or set(theme)!={'font','colors'} or theme['font']!='Microsoft YaHei':raise ValueError('This recipe currently uses Microsoft YaHei with measured metrics')
    colors=theme['colors'];roles=('ink','accent','muted','surface','background','line')
    if not isinstance(colors,dict) or not all(re.fullmatch('[0-9A-Fa-f]{6}',colors.get(c,'')) for c in roles):raise ValueError('Six role colors required')
    out=[];X,Y,W,H=(rect[k] for k in ('x','y','w','h'));nodes=model['nodes'];boxes={}
    def add(key,type,role,x,y,w,h,**payload):
        e=dict(id=eid+'-'+key,type=type,role=role,rect=dict(x=x,y=y,w=w,h=h),editability_requirement='native',fact_refs=[],group_id=eid,**payload);out.append(e);return e
    def text(key,value,x,y,w,h,size=18,color='ink',bold=False,role='body'):
        wrapped,needed=wrap_native(value,w,size,bold,max_lines=4)
        if needed>h:raise ValueError(f'{key}: text needs {needed:.2f}in, {h:.2f}in available; choose a wider/taller recipe')
        return add(key,'text',role,x,y,w,h,text=wrapped,style=dict(font_face=theme['font'],font_size_pt=size,color=colors[color],bold=bold))
    def shape(key,x,y,w,h,color='surface',geometry='roundRect'):
        return add(key,'shape','diagram',x,y,w,h,shape_kind=geometry,style=dict(fill=colors[color]))
    def edge(key,x,y,w,h,fromid,toid,fromsite,tosite,arrow=True):
        return add(key,'line','diagram',x,y,max(.001,w),max(.001,h),arrow_end=arrow,connection=dict(from_id=fromid,to_id=toid,from_site=fromsite,to_site=tosite),style=dict(color=colors['line']))
    if kind=='process':
        if len(nodes)>4:raise ValueError('Step/output recipe supports up to four steps at readable size')
        gap=.38;w=(W-gap*(len(nodes)-1))/len(nodes)
        for i,n in enumerate(nodes):boxes[n['id']]=(X+i*(w+gap),Y+.68,w,1.05)
        # Connectors go behind nodes and are bound to the real shape IDs later.
        for i,e in enumerate(model['edges']):
            a=boxes[e['from']];z=boxes[e['to']]
            edge('edge'+str(i),a[0]+a[2],a[1]+.525,z[0]-a[0]-a[2],.001,eid+'-'+e['from']+'-node',eid+'-'+e['to']+'-node',3,1)
            if e.get('label'):text('edge-label'+str(i),e['label'],a[0]+a[2]-.1,Y+.08,gap+.2,.5,12,'muted',role='caption')
        for i,n in enumerate(nodes):
            x,y,w,h=boxes[n['id']];key=n['id'];text(key+'-index',f'{i+1:02}',x,Y,w,.42,20,'accent',True)
            shape(key+'-node',x,y,w,h,'accent' if i==0 else 'surface','chevron')
            heading=text(key+'-label',n['label'],x+.55,y+.23,w-1.1,.61,21,'background' if i==0 else 'ink',True)
            heading['style']['align']='center'
            if n.get('body'):text(key+'-body',n['body'],x,Y+2.05,w,1.12,18,'muted')
            if n.get('output'):
                shape(key+'-output-line',x,Y+3.4,w,.025,'line','rect')
                text(key+'-output',n['output'],x,Y+3.58,w,H-3.58,16,'accent',role='caption')
    elif kind=='hierarchy':
        childw=(W-.35*(len(nodes)-2))/(len(nodes)-1);rootw=min(4.1,W*.42);rootx=X+(W-rootw)/2
        root=nodes[0];boxes[root['id']]=(rootx,Y,rootw,1.0)
        for i,n in enumerate(nodes[1:]):boxes[n['id']]=(X+i*(childw+.35),Y+2.0,childw,1.0)
        rootid=eid+'-'+root['id']+'-node'
        for i,n in enumerate(nodes[1:]):
            x,y,w,h=boxes[n['id']]
            # Fan-out lines bind the root bottom to each child's top.
            e=edge('edge'+str(i),min(rootx+rootw/2,x+w/2),Y+1,abs(x+w/2-rootx-rootw/2),1.0,rootid,eid+'-'+n['id']+'-node',2,0)
            e['connection']['flip_h']=x+w/2<rootx+rootw/2
        for i,n in enumerate(nodes):
            x,y,w,h=boxes[n['id']];key=n['id'];shape(key+'-node',x,y,w,h,'accent' if i==0 else 'surface')
            heading=text(key+'-label',n['label'],x+.18,y+.2,w-.36,.63,22,'background' if i==0 else 'ink',True)
            heading['style']['align']='center'
            if n.get('body'):text(key+'-body',n['body'],x,y+1.15,w,.96,18,'muted')
            if n.get('output'):raise ValueError('Hierarchy output annotation needs a different layout; do not omit it')
    else:
        dims=model['dimensions'];left=1.5;gap=.3;colw=(W-left-gap)/2;rowh=(H-.85)/len(dims)
        for j,n in enumerate(nodes):
            x=X+left+j*(colw+gap);shape(n['id']+'-band',x,Y,colw,.7,'accent' if j==0 else 'ink','rect');text(n['id']+'-label',n['label'],x+.2,Y+.12,colw-.4,.48,23,'background',True)
        for i,dim in enumerate(dims):
            y=Y+.85+i*rowh;text('dim'+str(i),dim,X,y+.14,left-.2,rowh-.18,18,'accent',True)
            for j,n in enumerate(nodes):
                x=X+left+j*(colw+gap)
                if i%2==0:shape(n['id']+'-row'+str(i),x,y,colw,rowh-.05,'surface','rect')
                text(n['id']+'-cell'+str(i),n['cells'][dim],x+.2,y+.12,colw-.4,rowh-.24,19)
    return dict(version='relationship-fragment/1',kind=kind,slide_id=request['slide_id'],source_refs=model['source_refs'],relationship=deepcopy(model),elements=out,group_id=eid,editability='native text, shapes and bound connectors; no SmartArt data part')

def prepare_relationship(input_path,out):
    input_path=local(input_path);out=fresh(out);fragment=compile_relationship(read(input_path));out.mkdir(parents=True)
    write(out/'request.json',read(input_path));write(out/'elements.json',fragment)
    return dict(status='prepared',fragment=str(out/'elements.json'),kind=fragment['kind'],element_count=len(fragment['elements']),source_refs=fragment['source_refs'],release_allowed=False)
