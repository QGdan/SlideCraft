"""Shared art direction → per-visual retrieval/prompt plans → actual usage record.

Original implementation; aesthetic decisions stay with the author, not tag scores.
"""
from copy import deepcopy
from pathlib import Path
import json,re,shutil
from .online_assets import ROOT,local,fresh,read,write,sha
from .assets import register_asset

def nonempty(x):return isinstance(x,str) and bool(x.strip())
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))

def validate_style(style):
    fields={'version','id','medium','colors','material','line','tone','references'}
    if not isinstance(style,dict) or set(style)!=fields or style['version']!='visual-style/1':raise ValueError('Exact visual-style/1 fields required')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',style.get('id','')):raise ValueError('Stable visual style ID required')
    if style['medium'] not in ('photography','illustration','mixed'):raise ValueError('Explicit style medium required')
    if not isinstance(style['colors'],dict) or not {'background','ink','accent'}<=style['colors'].keys() or not all(isinstance(v,str) and re.fullmatch('[A-Fa-f0-9]{6}',v) for v in style['colors'].values()):raise ValueError('Style role colors required')
    if not all(nonempty(style[k]) for k in ('material','line','tone')):raise ValueError('Style material, line and tone required')
    if not isinstance(style['references'],list) or not all(nonempty(x) for x in style['references']):raise ValueError('Style reference list required')
    return style

def validate_direction(d):
    if not isinstance(d,dict) or set(d)!={'role','medium','subject','aspect_ratio','negative_space','fit','avoid'}:raise ValueError('Exact visual_direction fields required')
    if d['role'] not in ('evidence','context','metaphor','decoration') or d['medium'] not in ('photography','illustration','icon'):raise ValueError('Explicit visual role and medium required')
    if not nonempty(d['subject']):raise ValueError('Visual subject required')
    m=re.fullmatch(r'([1-9][0-9]?):([1-9][0-9]?)',str(d['aspect_ratio']))
    if not m or not .2<=int(m[1])/int(m[2])<=5:raise ValueError('Aspect ratio must be a supported positive W:H ratio')
    if d['negative_space'] not in ('left','right','top','bottom','none') or d['fit'] not in ('contain','cover'):raise ValueError('Negative space and intended image fit required')
    if not isinstance(d['avoid'],list) or not all(nonempty(x) for x in d['avoid']):raise ValueError('Visual avoid list required')
    return d

def design_binding(style,direction):
    validate_style(style);validate_direction(direction)
    if style['medium']!='mixed' and direction['medium']!='icon' and style['medium']!=direction['medium']:raise ValueError('Visual medium conflicts with shared style; choose a coherent mixed style explicitly')
    return dict(style=deepcopy(style),style_sha256=digest(style),direction=deepcopy(direction))

def plan_assets(request,out):
    q=read(local(request));out=fresh(out)
    if not isinstance(q,dict) or not {'version','outline','brief'}<=q.keys() or set(q)-{'version','outline','brief','style'} or q['version']!='asset-plan-request/1':raise ValueError('asset-plan-request/1 needs outline, brief and optional style file')
    from .production_materials import validate_brief
    bp=local(q['brief']);op=local(q['outline']);brief=validate_brief(read(bp),read(op));style=validate_style(read(local(q['style'])) if 'style' in q else brief.get('asset_style'))
    tasks=[]
    for page in brief['slides']:
        for v in page['visuals']:
            if v['kind'] not in ('image','icon'):continue
            d=v.get('visual_direction')
            if d is None:raise ValueError('asset-plan requires visual_direction for every image/icon task')
            binding=design_binding(style,d);w,h=map(int,d['aspect_ratio'].split(':'));ratio=w/h
            query=' '.join(v['search_terms'])
            if not query:raise ValueError('Explicit search terms required for image/icon plan')
            orientation='landscape' if ratio>=1.2 else 'portrait' if ratio<=1/1.2 else 'square'
            prompt='\n'.join([f"Subject: {d['subject']}",f"Purpose: {v['purpose']}",f"Medium: {d['medium']}; role: {d['role']}",f"Aspect ratio: {d['aspect_ratio']}; negative space: {d['negative_space']}",f"Material: {style['material']}",f"Line: {style['line']}",f"Tone: {style['tone']}",f"Role colors: {json.dumps(style['colors'],ensure_ascii=False)}",f"Avoid: {'; '.join(d['avoid'])}",'Create an asset only. Titles, labels, data and charts are added as native PPT objects.'])
            tasks.append(dict(slide_id=page['id'],visual_id=v['id'],purpose=v['purpose'],design=binding,search=dict(query=query,keywords=query,provider='iconify' if v['kind']=='icon' else 'commons',orientation=orientation,min_width=0 if v['kind']=='icon' else 1600),planned_prompt=prompt,planned_references=style['references'],generation_eligible=d['role']!='evidence',review_questions=['主体是否支持本页主张？','画幅、留白和裁切后主体是否合适？','与共享风格和其他已选素材是否协调？'],status='planned_not_executed'))
    result=dict(version='asset-direction-plan/1',status='planned',outline_sha256=sha(op.read_bytes()),brief_sha256=sha(bp.read_bytes()),style=style,tasks=tasks)
    out.mkdir(parents=True);write(out/'asset-plan.json',result)
    for task in tasks:
        folder=out/task['slide_id']/task['visual_id'];folder.mkdir(parents=True)
        (folder/'planned-prompt.txt').write_text(task['planned_prompt']+'\n',encoding='utf-8');write(folder/'search-request.json',task['search'])
    return dict(status='planned',plan=str(out/'asset-plan.json'),tasks=len(tasks))

def record_asset(request,out):
    q=read(local(request));out=fresh(out)
    fields={'version','plan','slide_id','visual_id','preparation','operation','actual_tool','actual_prompt','actual_references','selection_reason','review_notes'}
    if not isinstance(q,dict) or set(q)!=fields or q['version']!='asset-record-request/1':raise ValueError('Exact asset-record-request/1 fields required')
    plan_path=local(q['plan']);plan=read(plan_path)
    if plan.get('version')!='asset-direction-plan/1':raise ValueError('Prepared asset direction plan required')
    matches=[t for t in plan['tasks'] if (t['slide_id'],t['visual_id'])==(q['slide_id'],q['visual_id'])]
    if len(matches)!=1:raise ValueError('Unique planned visual task required')
    task=matches[0];binding=design_binding(plan['style'],task['design']['direction'])
    if binding!=task['design']:raise ValueError('Asset plan style binding differs')
    if q['operation'] not in ('retrieved','existing','generated') or not all(nonempty(q[k]) for k in ('actual_tool','selection_reason','review_notes')):raise ValueError('Actual operation, tool and visual selection notes required')
    if not isinstance(q['actual_prompt'],str):raise ValueError('Actual prompt must be a string, empty for existing/retrieved')
    if q['operation']=='generated':
        if not task['generation_eligible'] or binding['direction']['role']=='evidence':raise ValueError('Generated images cannot fulfil documentary evidence tasks')
        if not q['actual_prompt'].strip():raise ValueError('Record the actual submitted prompt, not just the planned prompt')
    elif q['actual_prompt']:raise ValueError('Existing/retrieved assets do not have a new generation prompt')
    if not isinstance(q['actual_references'],list):raise ValueError('Actual local reference image list required')
    refs=[]
    for i,value in enumerate(q['actual_references']):
        from PIL import Image
        path=local(value)
        with Image.open(path) as image:image.verify()
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Reference image must be PNG/JPEG/WebP')
        refs.append(dict(original_path=str(path),file=f'reference-{i}'+path.suffix.lower(),sha256=sha(path.read_bytes())))
    original_p=local(q['preparation']);prep=deepcopy(read(original_p));a=prep['asset']
    if prep.get('status')!='prepared' or prep.get('source',{}).get('id')!=a['source_id'] or register_asset(local(a['path']),asset_id=a['id'],source_id=a['source_id'],license_note=a['license_note'])!=a:raise ValueError('Prepared asset bytes/source changed')
    record=dict(version='visual-design-record/1',**binding,slide_id=q['slide_id'],visual_id=q['visual_id'],plan_sha256=sha(plan_path.read_bytes()),planned_prompt=task['planned_prompt'],planned_references=task['planned_references'],operation=q['operation'],actual_tool=q['actual_tool'],actual_prompt=q['actual_prompt'],actual_references=refs,selection_reason=q['selection_reason'],review_notes=q['review_notes'])
    # A self-contained asset folder: snapshot original pixels and license sidecars.
    out.mkdir(parents=True);target=out/'image.png';shutil.copyfile(local(a['path']),target)
    for ref in refs:shutil.copyfile(local(ref['original_path']),out/ref['file'])
    for name in ('source.svg','LICENSE','download.bin','attribution.txt'):
        if (original_p.parent/name).is_file():shutil.copyfile(original_p.parent/name,out/name)
    prep['asset']=register_asset(target,asset_id=a['id'],source_id=a['source_id'],license_note=a['license_note']);prep['visual_design']=record
    write(out/'preparation.json',prep);write(out/'visual-design.json',record)
    return dict(status='prepared',preparation=str(out/'preparation.json'),record=str(out/'visual-design.json'),asset=prep['asset'])

def verify_design(prep,style,direction,slide_id,visual_id,preparation_path=None):
    expected=design_binding(style,direction);actual=prep.get('visual_design',{})
    if actual.get('version')!='visual-design-record/1' or any(actual.get(k)!=v for k,v in expected.items()) or actual.get('slide_id')!=slide_id or actual.get('visual_id')!=visual_id:raise ValueError('Prepared visual direction/style does not match this brief task')
    if actual.get('operation')=='generated' and (direction['role']=='evidence' or not nonempty(actual.get('actual_prompt'))):raise ValueError('Generated visual cannot replace evidence or omit actual prompt')
    if not isinstance(actual.get('actual_references'),list):raise ValueError('Actual references list required')
    for ref in actual['actual_references']:
        if not isinstance(ref,dict) or not re.fullmatch(r'reference-\d+\.(png|jpg|jpeg|webp)',ref.get('file','')):raise ValueError('Invalid recorded reference image')
        if preparation_path is not None:
            p=local(Path(preparation_path).parent/ref['file'])
            if sha(p.read_bytes())!=ref.get('sha256'):raise ValueError('Recorded reference image bytes changed')
    return actual
