"""Original structured templates with token-bound native content and raster slots."""
from pathlib import Path
import copy,hashlib,json,re,subprocess
from .assets import register_asset
from .contracts import validate
from .content import check_ledger,inspect_native
from .design import render_template
from .exhibits import compose_exhibit,compose_vertical_action
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def load_blueprint(template_id):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',template_id):raise ValueError('Invalid template ID')
    path=ROOT/'templates'/template_id/'blueprint.json'
    if not path.is_file():raise ValueError('Template blueprint not installed')
    return read(path),path
def catalog():
    return [{'id':b['id'],'name':b['name'],'variants':list(b['variants']),'layouts':list(b['layouts']),'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted((ROOT/'templates').glob('*/blueprint.json')) for b in [read(p)]]
def compile_blueprint(request,base_dir):
    if request.get('version')!='blueprint-request/1':raise ValueError('Unsupported blueprint request version')
    allowed={'version','template_id','variant','job_id','sources','facts','assets','slides'}
    if set(request)-allowed:raise ValueError('Unknown request fields')
    b,path=load_blueprint(request['template_id']);variant=request['variant']
    if variant not in b['variants']:raise ValueError('Unknown template variant')
    if not isinstance(request['slides'],list) or not 1<=len(request['slides'])<=20:raise ValueError('One to twenty slides required')
    colors=b['variants'][variant];font=b['font'];sizes=b['typography'];assets=[]
    for row in request.get('assets',[]):
        if set(row)!={'id','path','source_id','license_note'}:raise ValueError('Asset origin fields required')
        p=(Path(base_dir)/row['path']).resolve()
        if not p.is_relative_to(ROOT):raise ValueError('Image must stay inside project')
        assets.append(register_asset(p,asset_id=row['id'],source_id=row['source_id'],license_note=row['license_note']))
    if len({x['id'] for x in assets})!=len(assets):raise ValueError('Duplicate asset ID')
    facts={f['id']:f for f in request['facts']};pages=[]
    for n,page in enumerate(request['slides'],1):
        if set(page)-{'id','layout','fields','source_refs','notes','asset_id','image_focus','chart','items'}:raise ValueError('Unknown slide fields')
        key=page['layout']
        if key not in b['layouts']:raise ValueError('Unknown semantic layout')
        layout=b['layouts'][key];fields=page['fields'];limits=layout['field_limits']
        page_sizes={**sizes,**layout.get('typography_overrides',{})}
        if set(fields)!=set(layout['required_fields']):raise ValueError('Missing or extraneous layout fields')
        rendered={}
        for name,value in fields.items():
            if not isinstance(value,str) or not value.strip():raise ValueError('Nonempty text field required')
            text=render_template(value,facts)
            if len(text)>limits[name]:raise ValueError(f'{page["id"]}/{name}: rewrite or split; exceeds template capacity')
            rendered[name]=text
        sid=page['id'];elements=[]
        def rect(slot):return dict(zip(('x','y','w','h'),layout['regions'][slot]))
        def add_text(slot,size,color='ink',bold=False,role='body'):
            e=dict(id=f'{sid}-{slot}',type='text',role=role,rect=rect(slot),editability_requirement='native',fact_refs=re.findall(r'\{fact:([A-Za-z0-9_-]+)\}',fields[slot]),text=rendered[slot],style=dict(font_face=font,font_size_pt=page_sizes[size],color=colors[color],bold=bold))
            if e['fact_refs']:e['text_template']=fields[slot]
            elements.append(e)
        if layout.get('image_required'):
            asset=next((a for a in assets if a['id']==page.get('asset_id')),None)
            if not asset:raise ValueError('Scene layout requires registered asset')
            r=rect('image')
            if key=='scene_cover' and variant=='ink':r=dict(x=6.65,y=0,w=b['canvas']['width']-6.65,h=7.5)
            elements.append(dict(id=f'{sid}-scene',type='image',role='background',rect=r,editability_requirement='raster_allowed',fact_refs=[],asset_id=asset['id'],asset_path=asset['path'],image_fit='cover',image_focus=page.get('image_focus',{'x':.85,'y':.5})))
        add_text('title','cover' if key=='scene_cover' else 'title',bold=True,role='title')
        add_text('subtitle','body','muted')
        add_text('footer','footer','muted',role='source')
        if key=='scene_cover':add_text('kicker','kicker','accent',True,role='decoration')
        elif key=='evidence_focus':
            chart=copy.deepcopy(page['chart'])
            if len(chart['categories'])>layout['max_categories'] or len(chart['series'])>layout['max_series']:raise ValueError('Chart exceeds actual layout capacity')
            options=chart.setdefault('options',{});options.update(font_face=font,colors=dict(accent=colors['accent'],muted=colors['chart_muted'],ink=colors['ink'],series=[colors['accent'],colors['muted']]))
            elements.append(dict(id=f'{sid}-chart',type='chart',role='data',rect=rect('chart'),editability_requirement='native',fact_refs=[f for s in chart['series'] for f in s['fact_ids']],chart=chart))
            add_text('metric','metric','accent',True,role='data');add_text('body','body')
        else:
            kind='comparison' if key=='comparison_focus' else 'action'
            if kind=='action' and not 2<=len(page['items'])<=4:raise ValueError('Action template supports 2–4 steps')
            if key=='photo_process_side':elements+=compose_vertical_action(f'{sid}-exhibit',page['items'],rect('exhibit'),{'font':font,'colors':colors})
            else:elements+=compose_exhibit(kind,f'{sid}-exhibit',page['items'],rect('exhibit'),{'font':font,'colors':colors})
            if key=='comparison_focus':add_text('body','body',bold=True)
        elements.append(dict(id=f'{sid}-page',type='text',role='source',rect=dict(x=6.0 if key=='scene_cover' else 12.18,y=6.92,w=.4,h=.27),editability_requirement='native',fact_refs=[],text=f'{n:02}',style=dict(font_face=font,font_size_pt=sizes['footer'],color=colors['accent'])))
        pages.append(dict(id=sid,title=rendered['title'],message=rendered['title'],layout=key,background_color=colors['background'],notes=page['notes'],source_refs=page['source_refs'],elements=elements))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    spec=dict(schema_version='0.2',job_id=request['job_id'],canvas=b['canvas'],theme='provided_template',sources=request['sources'],facts=request['facts'],assets=assets,slides=pages,blueprint_ref=dict(id=b['id'],variant=variant,sha256=digest))
    errors=validate(spec,'deck')
    if errors:raise ValueError('; '.join(errors))
    ledger=check_ledger(spec)
    if ledger.issues:raise ValueError(json.dumps(ledger.issues,ensure_ascii=False))
    design={'font':font,'colors':colors,'layouts':[{'key':k,'name':k} for k in dict.fromkeys(s['layout'] for s in pages)],'semantic_layouts':{},'blueprint_sha256':digest}
    for key in dict.fromkeys(s['layout'] for s in pages):
        l=b['layouts'][key]
        design['semantic_layouts'][key]={'carriers':[l['carrier']],'max_body_characters':500,'min_body_font_pt':18,'max_chart_categories':l.get('max_categories',1),'max_chart_series':l.get('max_series',1)}
    return spec,design
def build_blueprint(input_path,out,node):
    input_path=Path(input_path).resolve();out=Path(out).resolve()
    if not input_path.is_relative_to(ROOT) or not input_path.is_file():raise ValueError('Project-local request required')
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh output directory inside runs required')
    spec,design=compile_blueprint(read(input_path),input_path.parent)
    out.mkdir(parents=True)
    for name,value in [('deck-spec.json',spec),('design-system.json',design)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    deck=out/'candidate.pptx'
    result=subprocess.run([str(node),str(ROOT/'engine/editorial_build.cjs'),str(out/'deck-spec.json'),str(deck)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    (out/'build.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise ValueError('Blueprint compiler failed; inspect build.log')
    native=inspect_native(deck,spec)
    report={'status':'failed' if native.issues else 'needs_review','deck':str(deck),'deck_sha256':hashlib.sha256(deck.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'blueprint':spec['blueprint_ref'],'native':native.__dict__,'release_allowed':False,'visual_review':'not_executed_by_cli'}
    (out/'blueprint-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
