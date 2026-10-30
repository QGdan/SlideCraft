"""Curated official figure artwork, kept separate from icons and project photos."""
from pathlib import Path
import hashlib,json,re,shutil
from PIL import Image
from .assets import register_asset
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'assets/illustrations/library.json'
def local(value):
    p=(ROOT/value).resolve()
    if not p.is_relative_to(ROOT/'assets/illustrations'):raise ValueError('Illustration path escapes library')
    return p
def load_illustrations():
    d=json.loads(CATALOG.read_text(encoding='utf-8'))
    if d.get('version')!='illustration-library/1':raise ValueError('Unsupported illustration catalog')
    ids=set();hashes=set()
    for row in d['assets']:
        if row['id'] in ids or row['svg_sha256'] in hashes:raise ValueError('Duplicate illustration')
        ids.add(row['id']);hashes.add(row['svg_sha256']);png=local(row['path']);svg=local(row['svg_path'])
        actual=register_asset(png,asset_id=row['id'],source_id=row['source_id'],license_note=row['license_note'])
        if any(actual[k]!=row[k] for k in ['sha256','width_px','height_px']) or hashlib.sha256(svg.read_bytes()).hexdigest()!=row['svg_sha256']:raise ValueError('Illustration changed')
        p=json.loads((svg.parent/'provenance.json').read_text(encoding='utf-8'))
        for file,key in [('source-page.html','source_page_sha256'),('CC0-legalcode.html','license_sha256')]:
            if hashlib.sha256((svg.parent/file).read_bytes()).hexdigest()!=p[key]:raise ValueError('Illustration source or license changed')
    return d
def prepare_illustration(asset_id,out,*,size=1024,slide_id,element_id,reason,color=None):
    if color is not None:raise ValueError('Illustrations preserve original colors; icon recoloring is not supported here')
    if isinstance(size,bool) or not isinstance(size,int) or not 64<=size<=1024:raise ValueError('Illustration size must be 64–1024 pixels')
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Selection reason required')
    if not all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',v) for v in [slide_id,element_id]):raise ValueError('Contract-compatible slide and element IDs required')
    row=next((r for r in load_illustrations()['assets'] if r['id']==asset_id),None)
    if row is None:raise ValueError('Unknown illustration')
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh preparation directory inside runs required')
    with Image.open(local(row['path'])) as im:
        image=im.convert('RGBA');image.thumbnail((size,size),Image.Resampling.LANCZOS)
    out.mkdir(parents=True);image.save(out/'image.png');shutil.copyfile(local(row['svg_path']),out/'source.svg');shutil.copyfile(local(row['path']).parent/'CC0-legalcode.html',out/'CC0-legalcode.html')
    asset=register_asset(out/'image.png',asset_id=element_id+'-asset' if len(element_id)<=57 else element_id,source_id=row['source_id'],license_note=row['license_note'])
    result=dict(status='prepared',asset=asset,source=dict(id=row['source_id'],kind='url',locator=row['upstream_url'],is_demo=False),selection=dict(library_id=asset_id,slide_id=slide_id,element_id=element_id,reason=reason,original_svg_sha256=row['svg_sha256'],max_size_px=size),files=dict(png=str(out/'image.png'),svg=str(out/'source.svg'),license=str(out/'CC0-legalcode.html')),editability='replaceable PNG; SVG retained; not native PPT shapes',release_allowed=False)
    (out/'preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result
