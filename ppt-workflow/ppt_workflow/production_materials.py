"""Detailed page briefs and task-local materials, before final template selection."""
from copy import deepcopy
from pathlib import Path
import re
import shutil
from .online_assets import ROOT,read,write,local,fresh,sha
from .assets import register_asset

MODE='outline-assets-template'

def text(value):
    return isinstance(value,str) and bool(value.strip())

def relationship_material(visual,files):
    if 'relationship' not in visual:return None
    fragments=[]
    for f in files:
        if f['role']=='source' and Path(f['path']).suffix.lower()=='.json':
            data=read(local(f['path']))
            if isinstance(data,dict) and data.get('version')=='relationship-fragment/1':fragments.append((f['path'],data))
    if len(fragments)!=1 or fragments[0][1].get('relationship')!=visual['relationship']:
        raise ValueError('Relationship material must match the detailed brief and include one prepared elements source')
    return fragments[0]

def frame_material(visual,files,page):
    if 'editorial_frame' not in visual:return None
    fragments=[]
    for f in files:
        if f['role']=='source' and Path(f['path']).suffix.lower()=='.json':
            data=read(local(f['path']))
            if isinstance(data,dict) and data.get('version')=='editorial-frame-fragment/1':fragments.append((f['path'],data))
    expected=dict(title=page['takeaway'],body_blocks=page['body_blocks'])
    if len(fragments)!=1 or fragments[0][1].get('frame')!=visual['editorial_frame'] or fragments[0][1].get('content')!=expected or fragments[0][1].get('slide_id')!=page['id']:
        raise ValueError('Frame material differs from this page title, original body or frame choice')
    if not set(fragments[0][1].get('source_refs',[]))<=set(visual['source_refs']):raise ValueError('Frame sources not declared by visual task')
    fragment=fragments[0][1];elements={e['id']:e for e in fragment['elements']};bindings=fragment.get('body_bindings',[])
    if [b.get('body_index') for b in bindings]!=list(range(len(page['body_blocks']))):raise ValueError('Frame body mapping omits or reorders original content')
    def same(a,b):return isinstance(a,str) and a.replace('\n','')==b.replace('\n','')
    titles=[e for e in elements.values() if e.get('role')=='title']
    if len(titles)!=1 or not same(titles[0].get('text'),page['takeaway']):raise ValueError('Frame title objects differ from original content')
    used=set()
    for b,original in zip(bindings,page['body_blocks']):
        ids=b.get('element_ids',[])
        if not ids or len(ids)!=len(set(ids)) or used.intersection(ids) or any(i not in elements or elements[i].get('type')!='text' for i in ids):raise ValueError('Frame body mapping needs distinct existing text objects')
        used.update(ids)
        if not same(''.join(elements[i]['text'] for i in ids),original):raise ValueError('Frame body objects differ from original content')
    fields=[('kicker',visual['editorial_frame']['kicker']),('footer',visual['editorial_frame']['footer'])]
    if visual['editorial_frame']['kind']=='divider':fields.append(('section',visual['editorial_frame']['section_label']))
    if visual['editorial_frame']['kind']=='closing':fields.extend(('heading'+str(i),h) for i,h in enumerate(visual['editorial_frame']['headings']))
    for suffix,value in fields:
        objects=[e for e in elements.values() if e['id'].endswith('-'+suffix)]
        if len(objects)!=1 or not same(objects[0].get('text'),value):raise ValueError('Frame label objects differ from authored labels')
    return fragments[0]

def validate_brief(brief,outline):
    if brief.get('version')!='production-brief/1':raise ValueError('Unsupported production brief')
    pages=brief.get('slides',[])
    if [(p.get('id'),p.get('takeaway')) for p in pages]!=[(p['id'],p['takeaway']) for p in outline['slides']]:
        raise ValueError('Detailed brief differs from approved outline page order/headlines')
    sources={s['id'] for s in outline['sources']};facts={f['id'] for f in outline['facts']}
    if 'asset_style' in brief:
        from .asset_direction import validate_style
        validate_style(brief['asset_style'])
    seen=set()
    for page in pages:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}',page['id']):raise ValueError('Invalid page ID')
        if not text(page.get('speaker_notes')) or not page.get('body_blocks') or not all(text(t) for t in page['body_blocks']):
            raise ValueError('Each page needs written body blocks and speaker notes')
        if not page.get('visuals'):raise ValueError('Each page needs a meaningful visual task')
        if 'reading_order' in page:
            if not isinstance(page['reading_order'],list) or not page['reading_order'] or not all(text(x) for x in page['reading_order']):raise ValueError('Explicit nonempty reading_order required')
        if 'dominant_evidence' in page and page['dominant_evidence'] not in {v['id'] for v in page['visuals']}:raise ValueError('Dominant evidence must name a visual task on this page')
        if 'layout_reason' in page and not text(page['layout_reason']):raise ValueError('Layout reason must be nonempty')
        for v in page['visuals']:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}',v.get('id','')) or (page['id'],v['id']) in seen:
                raise ValueError('Invalid/duplicate visual task ID')
            seen.add((page['id'],v['id']))
            if v.get('kind') not in ('image','icon','chart','diagram','table') or type(v.get('required')) is not bool:
                raise ValueError('Visual kind and required flag needed')
            if not all(text(v.get(k)) for k in ('purpose','composition_hint')):raise ValueError('Visual purpose and composition hint required')
            if not isinstance(v.get('search_terms'),list) or not all(text(t) for t in v['search_terms']):raise ValueError('Explicit search_terms list required')
            for key,known in [('source_refs',sources),('fact_refs',facts)]:
                if not isinstance(v.get(key),list) or any(x not in known for x in v[key]):raise ValueError('Unknown/missing visual source or fact references')
            if v['kind']=='chart' and not v['fact_refs']:raise ValueError('Data chart needs approved facts')
            if 'editorial_frame' in v:
                if v['kind']!='diagram' or 'relationship' in v:raise ValueError('Editorial frame is a native page composition, separate from a relationship diagram')
                from .editorial_frames import validate_frame
                validate_frame(v['editorial_frame'])
            if 'visual_direction' in v:
                if v['kind'] not in ('image','icon'):raise ValueError('visual_direction belongs to image/icon tasks')
                from .asset_direction import validate_direction,design_binding
                validate_direction(v['visual_direction'])
                if 'asset_style' in brief:design_binding(brief['asset_style'],v['visual_direction'])
            if 'relationship' in v:
                if v['kind']!='diagram':raise ValueError('Qualitative relationships belong to diagram visual tasks')
                from .relationships import validate_relationship
                validate_relationship(v['relationship'],sources)
                if not set(v['relationship']['source_refs'])<=set(v['source_refs']):raise ValueError('Relationship sources must be declared by its visual task')
    return brief

def build_pack(request,out):
    request=local(request);q=read(request);out=fresh(out)
    if q.get('version')!='materials-plan/1':raise ValueError('Unsupported materials plan')
    outline_path=local(q['outline']);brief_path=local(q['brief'])
    outline=read(outline_path);brief=validate_brief(read(brief_path),outline)
    style_path=local(q['asset_style']) if 'asset_style' in q else None
    style=read(style_path) if style_path else brief.get('asset_style')
    if style is not None:
        from .asset_direction import validate_style
        validate_style(style)
    wanted={(p['id'],v['id']):v for p in brief['slides'] for v in p['visuals']}
    seen=set();entries=[];copies=[]
    for item in q['items']:
        key=(item['slide_id'],item['visual_id'])
        if key not in wanted or key in seen or not text(item.get('reason')):raise ValueError('Unknown/duplicate selection or missing reason')
        seen.add(key);need=wanted[key]
        folder=out/key[0]/key[1]
        if not folder.resolve().is_relative_to(out):raise ValueError('Material path escapes pack')
        row=dict(slide_id=key[0],visual_id=key[1],kind=need['kind'],reason=item['reason'],files=[])
        if need['kind'] in ('image','icon'):
            prep_path=local(item['preparation']);prep=deepcopy(read(prep_path));a=prep['asset']
            if prep.get('status')!='prepared' or prep['source']['id']!=a['source_id']:raise ValueError('Prepared image and source required')
            original=local(a['path']);actual=register_asset(original,asset_id=a['id'],source_id=a['source_id'],license_note=a['license_note'])
            if actual!=a:raise ValueError('Prepared image bytes changed')
            if 'visual_direction' in need:
                from .asset_direction import verify_design
                design=verify_design(prep,style,need['visual_direction'],key[0],key[1],prep_path)
                for ref in design['actual_references']:copies.append((local(prep_path.parent/ref['file']),folder/ref['file']))
            target=folder/'image.png';copies.append((original,target))
            for name in ('source.svg','LICENSE','download.bin','attribution.txt'):
                p=prep_path.parent/name
                if p.is_file():copies.append((local(p),folder/name))
            prep['asset']['path']=str(target)
            prep['asset']['id']='packed-'+sha((key[0]+'/'+key[1]).encode())[:20]
            row.update(asset=deepcopy(prep['asset']),source=prep['source'],preparation=str(folder/'preparation.json'),
                       original_preparation_sha256=sha(prep_path.read_bytes()),credit_required=prep.get('credit_required',False))
            row['_preparation']=prep
        else:
            files=item.get('files',[])
            if not {'source','preview'}<={f.get('role') for f in files}:raise ValueError('Native visual needs editable source and actual preview files')
            relationship_material(need,files)
            frame_material(need,files,next(p for p in brief['slides'] if p['id']==key[0]))
            for index,f in enumerate(files):
                source=local(f['path']);target=folder/(str(index)+'-'+source.name)
                if f['role']=='preview':
                    from PIL import Image
                    with Image.open(source) as image:image.verify()
                copies.append((source,target));row['files'].append(dict(role=f['role'],path=str(target),sha256=sha(source.read_bytes())))
        entries.append(row)
    missing=[list(k) for k,v in wanted.items() if v['required'] and k not in seen]
    if missing:raise ValueError('Required visuals not prepared: '+str(missing))
    # Validate everything before writing a task-local snapshot.
    out.mkdir(parents=True)
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    for row in entries:
        if '_preparation' in row:write(Path(row['preparation']),row.pop('_preparation'))
    shutil.copyfile(outline_path,out/'content-outline.json');shutil.copyfile(brief_path,out/'production-brief.json')
    if style_path:shutil.copyfile(style_path,out/'asset-style.json')
    tracked=[dict(path=str(p),sha256=sha(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file()]
    manifest=dict(version='materials-pack/1',status='prepared',outline_sha256=sha(outline_path.read_bytes()),
        brief_sha256=sha(brief_path.read_bytes()),brief=str(out/'production-brief.json'),items=entries,files=tracked,
        missing_required=[],review='Human relevance/style/source review required before approving template',release_allowed=False)
    if style_path:manifest.update(asset_style=str(out/'asset-style.json'),asset_style_sha256=sha(style_path.read_bytes()))
    write(out/'manifest.json',manifest)
    return dict(status='prepared',manifest=str(out/'manifest.json'),items=len(entries),release_allowed=False)

def verify_pack(path,outline):
    path=local(path);pack=read(path)
    if pack.get('version')!='materials-pack/1' or pack.get('status')!='prepared' or pack.get('missing_required'):
        raise ValueError('Prepared materials pack required')
    tracked=[]
    for row in pack['files']:
        p=local(row['path'])
        if not p.is_relative_to(path.parent) or sha(p.read_bytes())!=row['sha256']:raise ValueError('Materials pack files changed or escaped')
        tracked.append(p)
    brief_path=local(pack['brief'])
    if brief_path not in tracked or sha(brief_path.read_bytes())!=pack['brief_sha256']:raise ValueError('Pack brief not bound')
    frozen=path.parent/'content-outline.json'
    if frozen not in tracked or sha(frozen.read_bytes())!=pack['outline_sha256'] or read(frozen)!=outline:
        raise ValueError('Pack belongs to another outline')
    brief=validate_brief(read(brief_path),outline)
    style=brief.get('asset_style')
    if 'asset_style' in pack:
        style_path=local(pack['asset_style'])
        if style_path not in tracked or sha(style_path.read_bytes())!=pack.get('asset_style_sha256'):raise ValueError('Shared asset style changed or not tracked')
        style=read(style_path)
    visual_tasks={(p['id'],v['id']):v for p in brief['slides'] for v in p['visuals']}
    needed={(p['id'],v['id']) for p in brief['slides'] for v in p['visuals'] if v['required']}
    present={(r['slide_id'],r['visual_id']) for r in pack['items']}
    if not needed<=present:raise ValueError('Pack omits required visuals')
    for row in pack['items']:
        if 'asset' in row:
            a=row['asset'];p=local(a['path'])
            if p not in tracked or register_asset(p,asset_id=a['id'],source_id=a['source_id'],license_note=a['license_note'])!=a:
                raise ValueError('Packed asset changed')
            if local(row['preparation']) not in tracked:raise ValueError('Preparation not tracked')
            prepared=read(row['preparation'])
            if prepared.get('asset')!=a or prepared.get('source')!=row['source']:raise ValueError('Packed preparation metadata differs')
            need=visual_tasks[(row['slide_id'],row['visual_id'])]
            if 'visual_direction' in need:
                from .asset_direction import verify_design
                design=verify_design(prepared,style,need['visual_direction'],row['slide_id'],row['visual_id'],row['preparation'])
                if any(local(Path(row['preparation']).parent/ref['file']) not in tracked for ref in design['actual_references']):raise ValueError('Reference image not tracked in material pack')
        else:
            if not {'source','preview'}<={f.get('role') for f in row['files']}:raise ValueError('Missing native source/preview')
            for f in row['files']:
                p=local(f['path'])
                if p not in tracked or sha(p.read_bytes())!=f['sha256']:raise ValueError('Native material not tracked or changed')
            relationship_material(visual_tasks[(row['slide_id'],row['visual_id'])],row['files'])
            frame_material(visual_tasks[(row['slide_id'],row['visual_id'])],row['files'],next(p for p in brief['slides'] if p['id']==row['slide_id']))
    return pack,tracked

def composition_sources_match(spec,outline):
    """Approved factual sources stay identical; only registered visual origins may append."""
    if spec['facts']!=outline['facts']:return False
    approved={s['id']:s for s in outline['sources']};actual={s['id']:s for s in spec['sources']}
    if len(actual)!=len(spec['sources']) or any(actual.get(k)!=v for k,v in approved.items()):return False
    visual_sources={a['source_id'] for a in spec.get('assets',[])}
    return all(sid in approved or sid in visual_sources for sid in actual)

def validate_packed_images(spec,pack):
    """Bind prepared images and relationship fragments to their actual page objects."""
    brief=read(pack['brief'])
    required={(p['id'],v['id']) for p in brief['slides'] for v in p['visuals'] if v['required']}
    allowed={(r['slide_id'],r['asset']['path'],r['asset']['sha256']):r for r in pack['items'] if 'asset' in r}
    needed={key for key,r in allowed.items() if (r['slide_id'],r['visual_id']) in required}
    assets={a['id']:a for a in spec.get('assets',[])};sources={s['id']:s for s in spec['sources']};used=set()
    for page in spec['slides']:
        for e in page['elements']:
            if e['type']!='image':continue
            a=assets.get(e.get('asset_id'),{});key=(page['id'],a.get('path'),a.get('sha256'));item=allowed.get(key)
            if not item or a!=item['asset'] or sources.get(a['source_id'])!=item['source']:
                raise ValueError('Image/source was not prepared for this page in approved materials pack')
            used.add(key)
            direction=read(item['preparation']).get('visual_design',{}).get('direction')
            if direction and e.get('image_fit')!=direction['fit']:raise ValueError('Image fit differs from prepared visual direction')
    if not needed<=used:raise ValueError('Required prepared images were omitted from composition')
    visual_tasks={(p['id'],v['id']):v for p in brief['slides'] for v in p['visuals']}
    pages={p['id']:p for p in spec['slides']}
    for row in pack['items']:
        visual=visual_tasks[(row['slide_id'],row['visual_id'])]
        if 'editorial_frame' in visual:
            page_brief=next(p for p in brief['slides'] if p['id']==row['slide_id'])
            _,fragment=frame_material(visual,row['files'],page_brief);page=pages.get(row['slide_id'],{});actual={e['id']:e for e in page.get('elements',[])}
            if not set(fragment['source_refs'])<=set(page.get('source_refs',[])):raise ValueError('Frame sources omitted from page')
            for expected in fragment['elements']:
                found=actual.get(expected['id'])
                if not found or any(found.get(k)!=expected.get(k) for k in ('type','text','group_id','shape_kind')):raise ValueError('Prepared frame copy or native object differs from composition')
        if 'relationship' not in visual:continue
        _,fragment=relationship_material(visual,row['files']);page=pages.get(row['slide_id'],{})
        actual={e['id']:e for e in page.get('elements',[])}
        if {e['id'] for e in page.get('elements',[]) if e.get('group_id')==fragment['group_id']}!={e['id'] for e in fragment['elements']}:
            raise ValueError('Prepared relationship group has omitted or unexpected objects')
        if not set(fragment['source_refs'])<=set(page.get('source_refs',[])):raise ValueError('Prepared relationship sources were omitted from slide')
        for expected in fragment['elements']:
            found=actual.get(expected['id'])
            if not found or any(found.get(k)!=expected.get(k) for k in ('type','text','group_id','shape_kind','connection')):
                raise ValueError('Prepared relationship node, copy or binding differs from composition')
