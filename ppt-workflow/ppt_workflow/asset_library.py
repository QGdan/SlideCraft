"""Small curated visual library. Tag search is not an aesthetic quality score."""
from pathlib import Path
import hashlib,html,json,os,re
from urllib.parse import quote
from .assets import register_asset
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'assets/library.json'
def load_library():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    if data.get('version')!='visual-library/1':raise ValueError('Unsupported visual library')
    seen_ids=set();seen_hashes=set()
    for row in data['assets']:
        path=(ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT/'assets'):raise ValueError('Library image escapes asset directory')
        actual=register_asset(path,asset_id=row['id'],source_id=row['source_id'],license_note=row['license_note'])
        if any(actual[k]!=row[k] for k in ('sha256','width_px','height_px')):raise ValueError('Library asset changed: '+row['id'])
        if row['id'] in seen_ids or row['sha256'] in seen_hashes:raise ValueError('Duplicate library asset; use aliases')
        seen_ids.add(row['id']);seen_hashes.add(row['sha256'])
    return data
def search_assets(query='',*,use=None,style=None,min_width=1,limit=8,asset_type='image',category=None):
    if isinstance(min_width,bool) or min_width<1 or not 1<=limit<=20:raise ValueError('Positive width and limit 1–20 required')
    if asset_type not in ('image','icon','illustration','all'):raise ValueError('Asset type must be image, icon, illustration or all')
    rows=[dict(row,type='image') for row in load_library()['assets']] if asset_type in ('image','all') else []
    if asset_type in ('icon','all'):
        from .icon_library import load_icons
        rows+=load_icons()['assets']
    if asset_type in ('illustration','all'):
        from .illustration_library import load_illustrations
        rows+=load_illustrations()['assets']
    terms=[t for t in re.split(r'[\s,，]+',query.casefold()) if t];found=[]
    synonyms={'团队':['协作','合作'],'科研':['研究','实验'],'教学':['教育','课堂'],'图表':['数据','统计'],'质检':['质量','审核'],'进度':['进度','计划','时间']}
    for row in rows:
        if use and use not in row['uses'] or style and style!=row['style_family'] or row['width_px']<min_width or category and category!=row.get('category'):continue
        hay=' '.join([row['title'],*row['tags']]).casefold();matches=[t for t in terms if any(s in hay for s in [t,*synonyms.get(t,[])])]
        if terms and not matches:continue
        item={**row,'path':str((ROOT/row['path']).resolve()),'matched_terms':matches}
        if row.get('svg_path'):item['svg_path']=str((ROOT/row['svg_path']).resolve())
        found.append(item)
    found.sort(key=lambda r:(-len(r['matched_terms']),r['id']))
    return {'status':'available','method':'local-curated-tag-match with curated Chinese synonyms; not aesthetic scoring','query':query,'filters':{'use':use,'style':style,'min_width_px':min_width,'type':asset_type,'category':category},'total_matches':len(found),'assets':found[:limit]}
def write_gallery(result,out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh gallery directory inside runs required')
    out.mkdir(parents=True);cards=[]
    for row in result['assets']:
        url=quote(os.path.relpath(row['path'],out).replace('\\','/'),safe='/')
        esc=html.escape
        cards.append(f'<article><a href="{url}"><img src="{url}" alt="{esc(row["title"])}"></a><h2>{esc(row["title"])}</h2><p>{esc(row["style_family"])} · {row["width_px"]}×{row["height_px"]}</p><p>用途：{esc(" / ".join(row["uses"]))}；留白：{esc(row["negative_space"])}</p><p>建议：{esc(row["placement_note"])}</p><p>边界：{esc("；".join(row["limitations"]))}</p><details><summary>来源与声明</summary><p>{esc(row["origin_record"])}</p><p>{esc(row["license_note"])}</p><code>{row["sha256"]}</code></details></article>')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本地视觉素材图册</title><style>body{font:16px system-ui,sans-serif;color:#183247;background:#f6f2ea;max-width:1200px;margin:40px auto;padding:0 20px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:32px}article{border-top:1px solid #c7c4bd;padding-top:20px}img{width:100%;height:260px;object-fit:contain;background:repeating-conic-gradient(#ddd 0% 25%,#eee 0% 50%) 0/20px 20px}p{line-height:1.65}code{overflow-wrap:anywhere}h1{font-size:30px}h2{font-size:21px}</style><h1>本地视觉素材图册</h1><p>按用途、风格、留白选素材。点击查看原图；合成图不能作为真实数据或活动证据。此页引用项目内原图，移动时请保持目录。</p><main>'+''.join(cards)+'</main></html>'
    (out/'index.html').write_text(page,encoding='utf-8')
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'html':str(out/'index.html'),'results':str(out/'results.json')}
