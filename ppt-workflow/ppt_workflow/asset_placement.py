"""Merge a prepared image into a specified slide without changing the input deck."""
from pathlib import Path
from copy import deepcopy
import math
import re
from .online_assets import fresh,local,read,write,sha
from .assets import register_asset,check_assets
from .contracts import validate

def inside(rect,canvas):
    if set(rect)!={'x','y','w','h'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in rect.values()):
        raise ValueError('Finite x/y/w/h rectangle required')
    x,y,w,h=[rect[k] for k in ('x','y','w','h')]
    if x<0 or y<0 or w<=0 or h<=0 or x+w>canvas['width']+1e-6 or y+h>canvas['height']+1e-6:
        raise ValueError('Image or credit rectangle outside canvas')

def place(request,out):
    request=local(request);q=read(request);out=fresh(out)
    required={'version','deck','preparation','slide_id','element_id','rect','fit','reason'}
    if not required<=q.keys() or set(q)-required-{'focus','credit_rect'} or q['version']!='asset-placement/1':
        raise ValueError('Unsupported placement contract')
    if not isinstance(q['reason'],str) or not q['reason'].strip():raise ValueError('Selection/placement reason required')
    eid=q['element_id']
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,54}',eid):raise ValueError('Element ID must leave room for credit suffix')
    source=local(q['deck']);prep_path=local(q['preparation']);deck=read(source);prep=read(prep_path)
    if prep.get('status')!='prepared':raise ValueError('Prepared asset required')
    errors=validate(deck,'deck')
    if errors:raise ValueError('Input deck invalid: '+str(errors[:3]))
    page=next((p for p in deck['slides'] if p['id']==q['slide_id']),None)
    if not page:raise ValueError('Slide absent from deck')
    if q['fit'] not in ('contain','cover'):raise ValueError('Explicit contain/cover required')
    design=prep.get('visual_design')
    if design and (design.get('slide_id')!=q['slide_id'] or design.get('direction',{}).get('fit')!=q['fit']):raise ValueError('Placement differs from prepared visual page/fit')
    if deck['schema_version']!='0.2' or deck['canvas']['unit']!='in':raise ValueError('Version 0.2 inch canvas required')
    inside(q['rect'],deck['canvas'])
    focus=q.get('focus',{'x':.5,'y':.5})
    if set(focus)!={'x','y'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in focus.values()):
        raise ValueError('Focus x/y must be in [0,1]')
    if prep.get('credit_required') and 'credit_rect' not in q:raise ValueError('CC BY asset needs visible credit_rect')
    if 'credit_rect' in q:inside(q['credit_rect'],deck['canvas'])
    used={e['id'] for p in deck['slides'] for e in p['elements']}
    if eid in used or eid+'-credit' in used:raise ValueError('Element ID already used')
    asset=prep['asset'];local(asset['path'])
    actual=register_asset(asset['path'],asset_id=asset['id'],source_id=asset['source_id'],license_note=asset['license_note'])
    if actual!=asset or prep['source']['id']!=asset['source_id']:raise ValueError('Prepared bytes/source changed')
    for collection,item in [('assets',asset),('sources',prep['source'])]:
        rows=deck.setdefault(collection,[]);existing=next((r for r in rows if r['id']==item['id']),None)
        if existing and existing!=item:raise ValueError('Conflicting asset/source ID')
        if not existing:rows.append(deepcopy(item))
    if asset['source_id'] not in page['source_refs']:page['source_refs'].append(asset['source_id'])
    element=dict(id=eid,type='image',role='body',rect=q['rect'],editability_requirement='raster_allowed',fact_refs=[],
                 asset_id=asset['id'],asset_path=asset['path'],image_fit=q['fit'],image_focus=focus)
    page['elements'].append(element)
    attribution=prep.get('attribution',asset['license_note'])
    processing='按区域裁切，原文件另存' if q['fit']=='cover' else '保持完整比例缩放'
    page['notes']+='\n素材：'+attribution+'\n处理：'+processing+'\n放置理由：'+q['reason']
    if 'credit_rect' in q:
        label=prep.get('selection',{})
        license_label=label.get('license_version') or label.get('license','')
        short=f'{label.get("title","素材")} / {label.get("creator","")} / {license_label}'
        if q['fit']=='cover':short+='（裁切）'
        if len(short)>160 or q['credit_rect']['h']<.25:raise ValueError('Credit needs shorter approved label or more space')
        page['elements'].append(dict(id=eid+'-credit',type='text',role='source',rect=q['credit_rect'],
            editability_requirement='native',fact_refs=[],text=short,style=dict(font_size_pt=10,color='5F6F78')))
    errors=validate(deck,'deck');integrity=check_assets(deck)
    if errors or integrity.issues:raise ValueError('Placed deck failed contract/asset checks: '+str(errors+integrity.issues)[:800])
    out.mkdir(parents=True);write(out/'deck-spec.json',deck)
    # Effective geometry is also checked in the actual renderer; no pixel-quality approval here.
    scale=(min if q['fit']=='contain' else max)(q['rect']['w']/asset['width_px'],q['rect']['h']/asset['height_px'])
    effective_ppi=1/scale
    overlaps=[]
    for other in page['elements']:
        if other['id'] in (eid,eid+'-credit') or other['role'] in ('background','decoration'):continue
        r=other['rect'];t=q['rect']
        if min(r['x']+r['w'],t['x']+t['w'])-max(r['x'],t['x'])>.01 and min(r['y']+r['h'],t['y']+t['h'])-max(r['y'],t['y'])>.01:
            overlaps.append(other['id'])
    report=dict(status='placed',deck_spec=str(out/'deck-spec.json'),input_sha256=sha(source.read_bytes()),
        preparation_sha256=sha(prep_path.read_bytes()),slide_id=q['slide_id'],element_id=eid,asset_id=asset['id'],
        rect=q['rect'],fit=q['fit'],focus=focus,reason=q['reason'],effective_ppi=round(effective_ppi,1),
        overlaps=overlaps,warnings=(['Raster below 120 effective PPI: reduce slot or select larger image'] if effective_ppi<120 else [])+(['Image overlaps existing content: review intentional layering'] if overlaps else []),
        visual_review='required; inspect crop, composition, credit and overlap in actual target application',release_allowed=False)
    write(out/'placement.json',report);return report
