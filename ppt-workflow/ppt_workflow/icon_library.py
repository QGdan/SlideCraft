"""Offline pinned SVG sources plus registered PNGs for the existing image engine."""
from pathlib import Path
import hashlib,json,re,shutil
import xml.etree.ElementTree as ET
from PIL import Image
from .assets import register_asset
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'assets/icons/library.json'

def local_asset(value):
    path=(ROOT/value).resolve()
    if not path.is_relative_to(ROOT/'assets/icons'):raise ValueError('Icon path escapes library')
    return path

def load_icons():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    if data.get('version')!='icon-library/1':raise ValueError('Unsupported icon library')
    seen=set();hashes=set()
    for row in data['assets']:
        if row['id'] in seen or row['svg_sha256'] in hashes:raise ValueError('Duplicate icon identity or bytes')
        seen.add(row['id']);hashes.add(row['svg_sha256'])
        png=local_asset(row['path']);svg=local_asset(row['svg_path'])
        actual=register_asset(png,asset_id=row['id'],source_id=row['source_id'],license_note=row['license_note'])
        if any(actual[k]!=row[k] for k in ('sha256','width_px','height_px')) or hashlib.sha256(svg.read_bytes()).hexdigest()!=row['svg_sha256']:raise ValueError('Icon content changed: '+row['id'])
        provenance=json.loads((svg.parent/'provenance.json').read_text(encoding='utf-8'))
        if provenance['commit']!=row['upstream_commit'] or hashlib.sha256((svg.parent/'LICENSE').read_bytes()).hexdigest()!=provenance['license_sha256']:raise ValueError('Icon license or provenance changed')
        root=ET.fromstring(svg.read_bytes())
        allowed={'svg','path','circle','rect','line','polyline','polygon','ellipse','g'}
        for node in root.iter():
            if node.tag.split('}')[-1] not in allowed:raise ValueError('Unsupported SVG content')
            if any(k.lower().startswith('on') or k.split('}')[-1] in ('href','style') for k in node.attrib):raise ValueError('Unsupported SVG attribute')
    return data

def prepare_icon(asset_id,out,*,color='162E3B',size=256,slide_id,element_id,reason):
    if not re.fullmatch(r'[0-9a-fA-F]{6}',color):raise ValueError('Six hexadecimal color digits required')
    if isinstance(size,bool) or not isinstance(size,int) or not 64<=size<=256:raise ValueError('PNG size must be integer 64–256; SVG remains vector')
    if not all(isinstance(v,str) and v.strip() for v in (slide_id,element_id,reason)):raise ValueError('Slide, element and selection reason required')
    if not all(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}',v) for v in (slide_id,element_id)):raise ValueError('Contract-compatible slide and element IDs required')
    row=next((r for r in load_icons()['assets'] if r['id']==asset_id),None)
    if not row:raise ValueError('Unknown icon: '+asset_id)
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh preparation directory inside runs required')
    color=color.upper();source=local_asset(row['svg_path'])
    # Previews have the original SVG's silhouette. Recolor alpha, never recolor the backdrop.
    with Image.open(local_asset(row['path'])) as im:
        mask=im.convert('RGBA').getchannel('A').resize((size,size),Image.Resampling.LANCZOS)
    image=Image.new('RGBA',(size,size),'#'+color);image.putalpha(mask)
    svg_text=source.read_text(encoding='utf-8').replace('currentColor','#'+color)
    out.mkdir(parents=True);image.save(out/'image.png');(out/'source.svg').write_text(svg_text,encoding='utf-8')
    shutil.copyfile(source.parent/'LICENSE',out/'LICENSE')
    registered=register_asset(out/'image.png',asset_id=element_id+'-asset' if len(element_id)<=57 else element_id,source_id=row['source_id'],license_note=row['license_note'])
    result=dict(status='prepared',asset=registered,source=dict(id=row['source_id'],kind='url',locator=row['upstream_url'],is_demo=False),
                selection=dict(library_id=asset_id,slide_id=slide_id,element_id=element_id,reason=reason,color=color,size_px=size,upstream_commit=row['upstream_commit'],original_svg_sha256=row['svg_sha256']),
                files=dict(png=str(out/'image.png'),svg=str(out/'source.svg'),license=str(out/'LICENSE')),
                editability='PNG image replaceable; SVG source retained; no native shape conversion',release_allowed=False)
    (out/'preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
