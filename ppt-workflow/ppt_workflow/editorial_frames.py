"""Native cover, chapter divider and action closing in one visual family."""
from copy import deepcopy
import re
from .online_assets import ROOT,local,fresh,read,write
from .textflow import wrap_native
from .layout_capacity import COLORS

def validate_frame(frame):
    common={'kind','kicker','footer'}
    if not isinstance(frame,dict) or frame.get('kind') not in ('cover','divider','closing'):raise ValueError('Supported editorial frame kind required')
    extra={'cover':set(),'divider':{'section_label'},'closing':{'headings'}}[frame['kind']]
    if set(frame)!=common|extra:raise ValueError('Exact frame fields required for this kind')
    if not all(isinstance(frame[k],str) and frame[k].strip() for k in ('kicker','footer')):raise ValueError('Actual frame kicker/footer required')
    if frame['kind']=='divider' and not re.fullmatch(r'\d{2}',frame.get('section_label','')):raise ValueError('Divider needs an explicit two-digit section label')
    if frame['kind']=='closing' and (not isinstance(frame['headings'],list) or not 1<=len(frame['headings'])<=3 or not all(isinstance(x,str) and x.strip() for x in frame['headings'])):raise ValueError('Closing needs one to three authored action headings')
    return frame

def compile_frame(q):
    fields={'version','slide_id','element_id','theme','frame','content','source_refs'}
    if not isinstance(q,dict) or set(q)!=fields or q['version']!='editorial-frame-request/1':raise ValueError('Exact editorial-frame-request/1 fields required')
    frame=validate_frame(q['frame']);content=q['content'];kind=frame['kind'];eid=q['element_id']
    for key in ('slide_id','element_id'):
        if not isinstance(q[key],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}',q[key]):raise ValueError('Stable short frame IDs required')
    if not isinstance(content,dict) or set(content)!={'title','body_blocks'} or not isinstance(content['title'],str) or not content['title'].strip():raise ValueError('Actual title and body_blocks required')
    blocks=content['body_blocks'];maximum={'cover':2,'divider':1,'closing':3}[kind]
    if not isinstance(blocks,list) or not 1<=len(blocks)<=maximum or not all(isinstance(x,str) and x.strip() for x in blocks):raise ValueError('Frame body capacity exceeded; keep original content and select another layout')
    if kind=='closing' and len(frame['headings'])!=len(blocks):raise ValueError('Closing headings must correspond to all original body blocks')
    theme=q['theme']
    if not isinstance(theme,dict) or set(theme)!={'font','colors'} or theme['font']!='Microsoft YaHei':raise ValueError('Measured frame uses Microsoft YaHei')
    colors=theme['colors']
    if not isinstance(colors,dict) or not all(isinstance(colors.get(k),str) and re.fullmatch('[A-Fa-f0-9]{6}',colors[k]) for k in COLORS):raise ValueError('Six frame role colors required')
    refs=q['source_refs']
    if not isinstance(refs,list) or not refs or len(refs)!=len(set(refs)) or not all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',x) for x in refs):raise ValueError('Distinct frame source references required')
    elements=[];body_bindings=[]
    def text(key,value,x,y,w,h,size=20,color='ink',bold=False,role='body',max_lines=2,group=None):
        wrapped,needed=wrap_native(value,w,size,bold,max_lines=max_lines)
        if needed>h:raise ValueError(f'{key}: frame text exceeds available height; select another frame or return to outline')
        e=dict(id=eid+'-'+key,type='text',role=role,rect=dict(x=x,y=y,w=w,h=h),text=wrapped,editability_requirement='native',fact_refs=[],style=dict(font_face=theme['font'],font_size_pt=size,color=colors[color],bold=bold))
        if group:e['group_id']=group
        elements.append(e);return e['id']
    def shape(key,x,y,w,h,color='surface',group=None):
        e=dict(id=eid+'-'+key,type='shape',role='decoration',rect=dict(x=x,y=y,w=w,h=h),shape_kind='rect',editability_requirement='native',fact_refs=[],style=dict(fill=colors[color]))
        if group:e['group_id']=group
        elements.append(e)
    text('kicker',frame['kicker'],.75,.48,11.85,.3,11,'accent',role='caption',max_lines=1)
    text('footer',frame['footer'],.75,6.98,11.1,.27,10,'muted',role='source',max_lines=1)
    if kind=='cover':
        text('title',content['title'],.75,1.55,8.0,1.6,38,bold=True,role='title')
        y=3.65
        for i,body in enumerate(blocks):
            wrapped,needed=wrap_native(body,7.5,22,max_lines=2)
            if y+needed>5.8:raise ValueError('Cover body exceeds reserved area')
            obj=text('body'+str(i),body,.75,y,7.5,needed+.01,22,'muted');body_bindings.append(dict(body_index=i,element_ids=[obj]));y+=needed+.23
        group=eid+'-motif'
        # Editable document sheets; these strokes do not encode quantitative data.
        shape('back-sheet',9.0,2.05,2.5,2.95,'line',group)
        shape('front-sheet',9.45,2.65,2.65,2.95,'surface',group)
        shape('document-heading',9.75,3.02,1.8,.24,'accent',group)
        for i in range(4):shape('document-line'+str(i),9.75,3.65+i*.34,1.8,.035,'line',group)
    elif kind=='divider':
        shape('marker',.75,1.88,.07,1.67,'accent')
        text('title',content['title'],1.08,1.9,8.85,1.65,36,bold=True,role='title')
        text('section',frame['section_label'],10.25,1.95,2.2,1.85,82,'line',True,role='caption',max_lines=1)
        obj=text('body0',blocks[0],1.08,4.13,9.7,1.12,22,'muted');body_bindings.append(dict(body_index=0,element_ids=[obj]))
        shape('line',1.08,5.78,11.22,.025,'line')
    else:
        text('title',content['title'],.75,1.0,11.85,1.3,34,bold=True,role='title')
        for i,(heading,body) in enumerate(zip(frame['headings'],blocks)):
            y=2.65+i*1.18;group=eid+'-row'+str(i)
            text('index'+str(i),f'{i+1:02}',.75,y,.6,.78,18,'accent',True,max_lines=1,group=group)
            text('heading'+str(i),heading,1.65,y,3.0,.78,20,'accent',True,max_lines=2,group=group)
            obj=text('body'+str(i),body,5.0,y,7.6,.78,19,'ink',group=group);body_bindings.append(dict(body_index=i,element_ids=[obj]))
            shape('rule'+str(i),1.65,y+.92,10.95,.018,'line',group)
    return dict(version='editorial-frame-fragment/1',slide_id=q['slide_id'],frame=deepcopy(frame),content=deepcopy(content),source_refs=deepcopy(refs),elements=elements,body_bindings=body_bindings,editability='native text/shapes; grouped cover motif and closing rows')

def prepare_frame(input_path,out):
    q=read(local(input_path));result=compile_frame(q);out=fresh(out);out.mkdir(parents=True)
    write(out/'request.json',q);write(out/'elements.json',result)
    return dict(status='prepared',fragment=str(out/'elements.json'),kind=result['frame']['kind'])

def frame_catalog():
    import hashlib
    p=ROOT/'templates/editorial-frames/library.json';catalog=read(p)
    for row in catalog['frames']:
        if row.get('preview'):
            preview=local(ROOT/row['preview'])
            if hashlib.sha256(preview.read_bytes()).hexdigest()!=row['preview_sha256']:raise ValueError('Frame preview changed')
            row['preview']=str(preview)
    return dict(status='available',frames=catalog['frames'],approval='not_implied')
