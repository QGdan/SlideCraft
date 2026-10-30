"""Assemble supported pages from existing outline, materials pack and layout choice.

No topic-specific scripts, source inventions, content truncation or stage approval.
"""
from copy import deepcopy
from pathlib import Path
import math,re
from .online_assets import local,fresh,read,write,sha
from .production_materials import verify_pack,validate_packed_images,composition_sources_match
from .layout_capacity import plan_layout,compile_pages,COLORS
from .textflow import wrap_native
from .contracts import validate
from .content import check_ledger

def nonempty(s):return isinstance(s,str) and bool(s.strip())

def native_fragment(row):
    allowed={'relationship-fragment/1','chart-style-fragment/1','trend-annotation-fragment/1','editorial-frame-fragment/1','compact-chart-fragment/1'}
    fragments=[]
    for f in row.get('files',[]):
        if f['role']=='source' and Path(f['path']).suffix.lower()=='.json':
            data=read(local(f['path']))
            if isinstance(data,dict) and data.get('version') in allowed:fragments.append(data)
    if len(fragments)!=1:raise ValueError('Native visual needs one supported prepared fragment in this task pack')
    return deepcopy(fragments[0])

def assemble(q):
    fields={'version','job_id','outline','materials_pack','design_system','pages'}
    if not isinstance(q,dict) or set(q)!=fields or q['version']!='brief-composition-request/1':raise ValueError('Exact brief-composition-request/1 fields required')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}',q.get('job_id','')):raise ValueError('Stable job ID required')
    op=local(q['outline']);mp=local(q['materials_pack']);dp=local(q['design_system'])
    outline=read(op);pack,_=verify_pack(mp,outline);brief=read(pack['brief']);design=read(dp)
    if design.get('font')!='Microsoft YaHei' or not isinstance(design.get('colors'),dict):raise ValueError('This assembler uses measured Microsoft YaHei and role colors')
    colors=design['colors']
    if not all(isinstance(colors.get(k),str) and re.fullmatch('[A-Fa-f0-9]{6}',colors[k]) for k in COLORS):raise ValueError('Design needs all six layout role colors')
    layouts={x['key'] for x in design['layouts']}
    if not isinstance(q['pages'],list) or [p.get('slide_id') for p in q['pages']]!=[p['id'] for p in outline['slides']]:raise ValueError('Composition must retain every outline page ID and its order')
    material={(r['slide_id'],r['visual_id']):r for r in pack['items']};want_pages={p['id']:p for p in brief['slides']}
    sources=deepcopy(outline['sources']);assets=[];slides=[];bindings=[];capacity=[]
    def merge(collection,item):
        old=next((x for x in collection if x['id']==item['id']),None)
        if old is not None and old!=item:raise ValueError('Source/asset ID conflicts with existing approved record')
        if old is None:collection.append(deepcopy(item))
    for n,choice in enumerate(q['pages'],1):
        common={'slide_id','visual_id','layout','kicker'}
        if not common<=choice.keys() or not nonempty(choice['kicker']):raise ValueError('Page needs slide_id, visual_id, layout and actual kicker')
        sid=choice['slide_id'];page=want_pages[sid];visuals={v['id']:v for v in page['visuals']};vid=choice['visual_id'];visual=visuals.get(vid);row=material.get((sid,vid))
        if not visual or row is None:raise ValueError('Selected visual must exist in this page task pack')
        selected={vid}
        if choice['layout']=='image-chart':
            if not nonempty(choice.get('chart_visual_id')):raise ValueError('Paired page needs a separate chart_visual_id')
            selected.add(choice['chart_visual_id'])
        if any(v['required'] and v['id'] not in selected for v in page['visuals']):raise ValueError('Multiple required visuals need another composition; do not omit them')
        if choice['layout'] not in layouts:raise ValueError('Selected layout is absent from the design system')
        refs=list(dict.fromkeys([*outline['slides'][n-1].get('evidence_refs',[]),*(r for v in page['visuals'] if v['id'] in selected for r in v['source_refs'])]))
        # evidence_refs can refer to facts; slide source_refs contain source IDs only.
        facts={f['id']:f for f in outline['facts']};known={s['id'] for s in sources}
        refs=list(dict.fromkeys(facts[x]['source_id'] if x in facts else x for x in refs))
        if any(x not in known for x in refs):raise ValueError('Unknown page source reference')
        if not refs:refs=[s['id'] for s in outline['sources'] if not s.get('is_demo')]
        elements=[];body_map=[];paired_map=None
        def text(key,value,x,y,w,h,size=19,color='ink',bold=False,role='body'):
            elements.append(dict(id=f'brief{n}-{key}',type='text',role=role,rect=dict(x=x,y=y,w=w,h=h),text=value,editability_requirement='native',fact_refs=[],style=dict(font_face=design['font'],font_size_pt=size,color=colors[color],bold=bold)))
        if choice['layout']=='image-chart':
            from .paired_evidence import IMAGE_SLOT
            allowed=common|{'chart_visual_id','image_heading','image_note','focus'}
            if set(choice)-allowed or not all(nonempty(choice.get(k)) for k in ('image_heading','image_note')):raise ValueError('Image/chart choice needs image_heading/image_note and supported fields only')
            chart_id=choice['chart_visual_id'];chart_visual=visuals.get(chart_id);chart_row=material.get((sid,chart_id))
            if visual['kind']!='image' or not chart_visual or chart_visual['kind']!='chart' or not chart_row or chart_id==vid:raise ValueError('Image/chart pair needs separate prepared image and chart on this page')
            fragment=native_fragment(chart_row)
            if fragment.get('version')!='compact-chart-fragment/1' or fragment.get('slide_id')!=sid:raise ValueError('Paired page requires its own prepared compact chart; do not shrink a full chart/callout silently')
            if any(s not in sources for s in fragment['sources']) or any(facts.get(f['id'])!=f for f in fragment['facts']):raise ValueError('Paired chart sources/facts differ from outline')
            title,th=wrap_native(page['takeaway'],11.85,30,True,max_lines=1);text('title',title,.75,1,11.85,max(.65,th),30,bold=True,role='title')
            text('kicker',choice['kicker'],.75,.42,11.85,.28,11,'accent',role='caption')
            body,_=wrap_native('\n'.join(page['body_blocks']),11.85,17,max_lines=1);text('body',body,.75,1.83,11.85,.37,17,'muted');body_map=[dict(body_index=i,element_ids=[f'brief{n}-body']) for i in range(len(page['body_blocks']))]
            heading,_=wrap_native(choice['image_heading'],4.8,18,True,max_lines=1);text('image-heading',heading,.75,2.38,4.8,.42,18,bold=True,role='caption')
            a=row['asset'];prep=read(row['preparation']);merge(assets,a);merge(sources,row['source']);refs=list(dict.fromkeys([*refs,row['source']['id'],*fragment['source_refs']]))
            focus=choice.get('focus',dict(x=.5,y=.5))
            if not isinstance(focus,dict) or set(focus)!={'x','y'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in focus.values()):raise ValueError('Finite image focus in [0,1] required')
            fit=visual.get('visual_direction',{}).get('fit','contain')
            elements.append(dict(id=f'brief{n}-image',type='image',role='body',rect=deepcopy(IMAGE_SLOT),editability_requirement='raster_allowed',fact_refs=[],asset_id=a['id'],asset_path=a['path'],image_fit=fit,image_focus=focus))
            note=choice['image_note']
            if prep.get('credit_required'):
                meta=prep.get('selection',{});credit=' / '.join(str(meta.get(k,'')) for k in ('title','creator','license')).strip(' /')
                if not credit:raise ValueError('Paired image needs visible attribution')
                note+='\n'+credit
            note,nh=wrap_native(note,4.8,10,max_lines=2);text('image-note',note,.75,6.55,4.8,max(.44,nh),10,'muted',role='source')
            elements+=fragment['elements'];paired_map={vid:[f'brief{n}-image'],chart_id:[e['id'] for e in fragment['elements']]}
        elif 'editorial_frame' in visual:
            if set(choice)!=common:raise ValueError('Frame page uses its prepared kicker/footer; no duplicate extra fields')
            fragment=native_fragment(row)
            expected_content=dict(title=page['takeaway'],body_blocks=page['body_blocks'])
            if fragment.get('version')!='editorial-frame-fragment/1' or fragment.get('slide_id')!=sid or fragment.get('frame')!=visual['editorial_frame'] or fragment.get('content')!=expected_content:raise ValueError('Frame fragment does not match original page content')
            if choice['layout']!=fragment['frame']['kind'] or choice['kicker']!=fragment['frame']['kicker']:raise ValueError('Frame layout/kicker differs from selected prepared frame')
            elements+=fragment['elements'];body_map=deepcopy(fragment['body_bindings']);refs=list(dict.fromkeys([*refs,*fragment['source_refs']]))
        elif visual['kind'] in ('image','icon'):
            if set(choice)-common-{'sections','source_note','focus'}:raise ValueError('Unknown image page choice field')
            sections=choice.get('sections')
            if not isinstance(sections,list) or [s.get('body_index') for s in sections]!=list(range(len(page['body_blocks']))):raise ValueError('Image sections must cover every body block once in original order')
            blocks=[]
            for i,s in enumerate(sections):
                if set(s)!={'body_index','heading'} or not nonempty(s['heading']):raise ValueError('Section needs original body_index and an authored heading')
                blocks.append(dict(id='body'+str(i),heading=s['heading'],text=page['body_blocks'][i]))
            request=dict(version='layout-request/1',slide_id='brief'+str(n),title=page['takeaway'],kicker=choice['kicker'],source_note=choice.get('source_note'),evidence='image',layout=choice['layout'],page_limit=1,colors={k:colors[k] for k in COLORS},blocks=blocks)
            planned=plan_layout(request)
            if planned['status']!='planned':raise ValueError(f'{sid}: content needs {planned["page_count"]} pages; change layout or return proposed split to outline')
            fragment=compile_pages(planned);elements=fragment['slides'][0]['elements'];slot=planned['pages'][0]['evidence_rect']
            if slot is None:raise ValueError('Image layout must expose a supported image slot')
            for i in range(len(blocks)):
                part_indices=[j for j,part in enumerate(planned['pages'][0]['parts']) if part['block_id']=='body'+str(i)]
                body_map.append(dict(body_index=i,element_ids=[e['id'] for e in elements if any(e['id'].endswith('-b'+str(j)) for j in part_indices)]))
            capacity.append(dict(slide_id=sid,plan=planned))
            a=row['asset'];prep=read(row['preparation']);merge(assets,a);merge(sources,row['source'])
            refs=list(dict.fromkeys([*refs,row['source']['id']]))
            direction=visual.get('visual_direction',{});fit=direction.get('fit','contain');focus=choice.get('focus',dict(x=.5,y=.5))
            if not isinstance(focus,dict) or set(focus)!={'x','y'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in focus.values()):raise ValueError('Finite image focus in [0,1] required')
            elements.append(dict(id=f'brief{n}-image',type='image',role='body',rect=slot,editability_requirement='raster_allowed',fact_refs=[],asset_id=a['id'],asset_path=a['path'],image_fit=fit,image_focus=focus))
            if prep.get('credit_required'):
                meta=prep.get('selection',{});label=' / '.join(str(meta.get(k,'')) for k in ('title','creator','license')).strip(' /')
                if not label:raise ValueError('Visible short attribution label required')
                wrapped,_=wrap_native(label,11.85,10,max_lines=1)
                text('credit',wrapped,.75,6.7,11.85,.25,10,'muted',role='source')
        elif visual['kind'] in ('chart','diagram'):
            if set(choice)-common-{'source_note'}:raise ValueError('Unknown native page choice field')
            fragment=native_fragment(row)
            expected={'chart':{'chart-style-fragment/1','trend-annotation-fragment/1'},'diagram':{'relationship-fragment/1'}}[visual['kind']]
            if fragment['version'] not in expected or fragment.get('slide_id')!=sid:raise ValueError('Prepared native fragment has wrong page/type')
            for source in fragment.get('sources',[]):
                if source not in sources:raise ValueError('Native visual introduces a source absent from outline')
            if any(facts.get(f['id'])!=f for f in fragment.get('facts',[])):raise ValueError('Native visual facts differ from approved outline')
            if visual['kind']=='diagram' and fragment.get('relationship')!=visual.get('relationship'):raise ValueError('Prepared relationship differs from brief')
            for e in fragment['elements']:
                r=e['rect']
                if r['x']<.7 or r['y']<2.23 or r['x']+r['w']>12.65 or r['y']+r['h']>6.76:raise ValueError('Prepared visual overlaps reserved title/footer; prepare it in the supported content region')
            title,th=wrap_native(page['takeaway'],11.85,30,True,max_lines=1)
            text('kicker',choice['kicker'],.75,.42,11.85,.28,11,'accent',role='caption')
            text('title',title,.75,1,11.85,max(.65,th),30,bold=True,role='title')
            subtitle='\n'.join(page['body_blocks']);subtitle,_=wrap_native(subtitle,11.85,17,max_lines=1)
            text('body',subtitle,.75,1.83,11.85,.37,17,'muted')
            body_map=[dict(body_index=i,element_ids=[f'brief{n}-body']) for i in range(len(page['body_blocks']))]
            elements+=fragment['elements'];refs=list(dict.fromkeys([*refs,*fragment.get('source_refs',[])]))
            if visual['kind']=='diagram':
                note=choice.get('source_note')
                if not nonempty(note):raise ValueError('Native relationship page needs a short source_note')
                note,_=wrap_native(note,11.85,10,max_lines=1);text('source',note,.75,6.98,11.85,.27,10,'muted',role='source')
            elif 'source_note' in choice:raise ValueError('Chart material already owns its source note; do not add duplicate source_note')
        else:raise ValueError('Unsupported visual type; use existing dedicated compiler rather than placeholders')
        for e in elements:
            style=e.get('style',{})
            if style.get('font_face',design['font'])!=design['font'] or any(style[k] not in colors.values() for k in ('color','fill') if k in style):raise ValueError('Prepared visual style differs from selected design; prepare it in the selected style')
        # Remove local page counters and write one deck-wide counter.
        elements=[e for e in elements if not e['id'].endswith('-page')]
        text('page',f'{n:02}',12.1,7.02,.5,.25,10,'accent',role='source')
        slides.append(dict(id=sid,title=page['takeaway'],message=page['takeaway'],layout=choice['layout'],notes=page['speaker_notes'],background_color=colors['background'],source_refs=refs,elements=elements))
        if paired_map:visual_elements=[eid for ids in paired_map.values() for eid in ids]
        elif visual['kind'] in ('chart','diagram'):visual_elements=[e['id'] for e in fragment['elements']]
        else:visual_elements=[f'brief{n}-image']
        bindings.append(dict(slide_id=sid,visual_id=vid,visual_ids=[v['id'] for v in page['visuals'] if v['id'] in selected],body_blocks=body_map,visual_elements=visual_elements,visual_elements_by_id=paired_map,unused_optional_visuals=[v['id'] for v in page['visuals'] if v['id'] not in selected]))
    spec=dict(schema_version='0.2',job_id=q['job_id'],canvas=dict(width=13.333,height=7.5,unit='in'),theme='provided_template',sources=sources,facts=deepcopy(outline['facts']),assets=assets,slides=slides)
    errors=validate(spec,'deck')
    if errors:raise ValueError('Assembled deck invalid: '+str(errors[:3]))
    if not composition_sources_match(spec,outline):raise ValueError('Composition changed original facts or factual sources')
    validate_packed_images(spec,pack)
    ledger=check_ledger(spec)
    if ledger.issues:raise ValueError('Assembled fact bindings invalid: '+str(ledger.issues[:3]))
    return spec,dict(version='brief-composition-bindings/1',outline_sha256=sha(op.read_bytes()),materials_pack_sha256=sha(mp.read_bytes()),design_sha256=sha(dp.read_bytes()),pages=bindings,capacity=capacity)

def compose_brief(input_path,out,node):
    request=local(input_path);out=fresh(out);q=read(request);spec,bindings=assemble(q)
    out.mkdir(parents=True);write(out/'deck-spec.json',spec);write(out/'bindings.json',bindings)
    from .editorial_builder import build_editorial
    result=build_editorial(out/'deck-spec.json',out/'build',node,local(q['design_system']))
    handoff=dict(deck=result['deck'],deck_spec=str(out/'deck-spec.json'),implementation_notes='Composed from original page IDs, all body blocks, selected design and verified task materials; actual rendering and stage review remain required.')
    write(out/'composition.json',handoff)
    return dict(status='built',deck=result['deck'],spec=str(out/'deck-spec.json'),bindings=str(out/'bindings.json'),composition=str(out/'composition.json'),release_allowed=False)
