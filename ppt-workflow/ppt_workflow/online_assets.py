"""Explicit online discovery, bounded downloads and reusable on-disk cache.

Search metadata is a candidate, not approval of relevance or rights. No API keys
are required for the public endpoints used here; provider failures stay visible.
"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
import concurrent.futures
import hashlib
import html
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import urllib.request
from defusedxml import ElementTree as ET
from PIL import Image
from .assets import register_asset

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'assets/online-cache'
WORDS = {'汽车':'car','教育':'school','教学':'school','医疗':'medical',
         '工业':'factory','农业':'agriculture','科技':'technology','科研':'microscope',
         '团队':'users','协作':'teamwork','能源':'energy','光伏':'solar panel',
         '太阳能':'solar panel','交通':'transport','物流':'truck','建筑':'building',
         '环保':'environment','数据':'chart','金融':'finance','城市':'city',
         '学校':'school','课堂':'classroom','健康':'health','食品':'food',
         '实验':'laboratory','机器人':'robot','人工智能':'artificial intelligence'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
        stream.write(json.dumps(data,ensure_ascii=False,indent=2));temporary=stream.name
    os.replace(temporary,path)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def fresh(out):
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():
        raise ValueError('Fresh output directory inside runs required')
    return out

def local(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('Existing project-local file required')
    return path

def public_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
        raise ValueError('Public HTTPS URL required')
    addresses = socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Non-public download address rejected')
    return url

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(url, limit=2_000_000):
    public_url(url)
    request = urllib.request.Request(url,headers={'User-Agent':'PPT-Workflow-Asset-Research/1.0'})
    with urllib.request.build_opener(PublicRedirect()).open(request,timeout=15) as r:
        data = r.read(limit+1)
        if len(data)>limit:raise ValueError('Download exceeds size limit')
    return data

def json_query(url, offline=False):
    path = CACHE/'queries'/(sha(url.encode())+'.json')
    if offline:
        if not path.is_file():raise ValueError('No cached response for this exact query/page')
        envelope=read(path)
        raw=json.dumps(envelope['response'],ensure_ascii=False,sort_keys=True).encode()
        if sha(raw)!=envelope['response_sha256']:raise ValueError('Cached response changed')
        return envelope['response'], {'mode':'offline-cache','retrieved_at':envelope['retrieved_at']}
    data=json.loads(download(url))
    now=datetime.now(timezone.utc).isoformat()
    write(path,{'url':url,'retrieved_at':now,'response':data,
                'response_sha256':sha(json.dumps(data,ensure_ascii=False,sort_keys=True).encode())})
    return data, {'mode':'network','retrieved_at':now}

def expanded_query(query, keywords=None):
    query=query.strip()
    if not query or len(query)>200:raise ValueError('Query length must be 1–200')
    if keywords:
        if len(keywords)>200:raise ValueError('Keywords too long')
        return keywords.strip()
    terms=re.split(r'[\s,，]+',query)
    result=' '.join(WORDS.get(t,t) for t in terms)
    if re.search(r'[\u4e00-\u9fff]',result):
        raise ValueError('Unmapped Chinese terms: supply explicit --keywords in English')
    return result

def provider_search(provider, query, page, limit, offline):
    if provider=='iconify':
        query={'agriculture':'tractor','technology':'cpu','environment':'leaf',
               'energy':'bolt','transport':'bus','finance':'coins','solar panel':'solar-panel',
               'artificial intelligence':'brain'}.get(query,query)
        # Iconify minimum page size is 32; slice only the displayed candidates.
        url='https://api.iconify.design/search?'+urlencode(dict(query=query,prefix='tabler',limit=32,start=(page-1)*limit))
        data,state=json_query(url,offline)
        info=data.get('collections',{}).get('tabler',{})
        if data.get('icons') and info.get('license',{}).get('spdx')!='MIT':raise ValueError('Unexpected Tabler license metadata')
        rows=[]
        for name in data['icons'][:limit]:
            if not re.fullmatch(r'tabler:[a-z0-9-]+',name) or name.endswith('-filled'):continue
            rows.append(dict(id='iconify:'+name,provider=provider,type='icon',title=name.split(':')[1],
                upstream_id=name,download_url='https://api.iconify.design/'+name.replace(':','/')+'.svg',
                preview_url='https://api.iconify.design/'+name.replace(':','/')+'.svg',
                source_url='https://icon-sets.iconify.design/tabler/'+name.split(':')[1]+'/',
                creator=info.get('author',{}).get('name','Tabler contributors'),license='MIT',
                license_url=info['license'].get('url',''),style_family='tabler-outline',
                collection_version=info.get('version'),width=24,height=24))
        more=len(data['icons'])>limit
        total=info.get('total')
    elif provider=='openverse':
        url='https://api.openverse.org/v1/images/?'+urlencode(dict(q=query,page=page,page_size=limit,license='cc0,by',mature='false'))
        data,state=json_query(url,offline);rows=[]
        for item in data['results']:
            if item.get('license') not in ('cc0','by') or item.get('mature'):continue
            rows.append(dict(id='openverse:'+item['id'],upstream_id=item['id'],provider=provider,type='image',
                title=item.get('title') or 'Untitled',download_url=item['url'],preview_url=item.get('thumbnail',''),
                source_url=item['foreign_landing_url'],creator=item.get('creator') or '',
                license=item['license'],license_version=item.get('license_version',''),license_url=item.get('license_url',''),
                style_family='unreviewed-photo',width=item.get('width'),height=item.get('height')))
        more=page<data.get('page_count',page);total=None
    else:
        url='https://commons.wikimedia.org/w/api.php?'+urlencode(dict(action='query',format='json',
            generator='search',gsrsearch=query+' filetype:bitmap',gsrnamespace=6,gsrlimit=limit,
            gsroffset=(page-1)*limit,prop='imageinfo',iiprop='url|size|extmetadata',iiurlwidth=1280))
        data,state=json_query(url,offline)
        if 'error' in data:raise ValueError(str(data['error']))
        rows=[]
        for item in sorted(data.get('query',{}).get('pages',{}).values(),key=lambda x:x.get('index',0)):
            info=item.get('imageinfo',[{}])[0];meta=info.get('extmetadata',{})
            value=lambda k:str(meta.get(k,{}).get('value',''))
            label=value('LicenseShortName');license_url=value('LicenseUrl')
            if label=='CC0':lic='cc0'
            elif re.fullmatch(r'CC BY [0-9.]+',label):lic='by'
            else:continue
            if not license_url or value('Restrictions'):continue
            if license_url.startswith('//'):license_url='https:'+license_url
            creator=html.unescape(re.sub('<[^>]+>','',value('Artist'))).strip()
            rows.append(dict(id='commons:'+str(item['pageid']),upstream_id=str(item['pageid']),provider=provider,type='image',
                title=item['title'].removeprefix('File:'),download_url=info['url'],preview_url=info.get('thumburl',info['url']),
                source_url=info['descriptionurl'],creator=creator,license=lic,license_version=label,
                license_url=license_url,style_family='unreviewed-photo',width=info.get('width'),height=info.get('height')))
        more='continue' in data;total=None
    return dict(provider=provider,status='available' if rows else 'empty',request_url=url,
                page=page,next_page=page+1 if more else None,collection_size_reported=total,
                returned_before_display_limit=len(rows),assets=rows[:limit],**state)

def discover(query, out, *, provider='all', keywords=None, page=1, limit=8, offline=False, orientation='any', min_width=0):
    out=fresh(out)
    if provider not in ('all','iconify','openverse','commons','cache') or type(page)!=int or not 1<=page<=100 or type(limit)!=int or not 1<=limit<=20:
        raise ValueError('Provider/page/limit outside supported bounds')
    expanded=expanded_query(query,keywords)
    if orientation not in ('any','landscape','portrait','square') or type(min_width)!=int or min_width<0:
        raise ValueError('Unsupported orientation or minimum width')
    providers=['iconify','openverse','commons'] if provider=='all' else [provider]
    def one(p):
        try:
            if p=='cache':
                rows=[];seen=set()
                for manifest in sorted((CACHE/'selected').glob('*/manifest.json')):
                    record=read(manifest);row=record['row'];hay=' '.join(str(v) for v in row.values()).casefold()
                    if row['id'] not in seen and any(t.casefold() in hay for t in expanded.split()):
                        if any(sha((manifest.parent/name).read_bytes())!=digest for name,digest in record['files'].items()):raise ValueError('Selected cache changed')
                        rows.append(row);seen.add(row['id'])
                result=dict(provider=p,status='available' if rows else 'empty',assets=rows,total_cached_matches=len(rows),mode='selected-cache')
            else:result=provider_search(p,expanded,page,limit,offline)
            kept=[]
            for row in result['assets']:
                if row['type']=='image':
                    w,h=row.get('width') or 0,row.get('height') or 0
                    if w<min_width:continue
                    if orientation!='any' and (not w or not h):continue
                    if orientation=='landscape' and w/h<1.2:continue
                    if orientation=='portrait' and w/h>1/1.2:continue
                    if orientation=='square' and not .8333<=w/h<=1.2:continue
                kept.append(row)
            result['assets']=kept[(page-1)*limit:page*limit] if p=='cache' else kept
            result['status']='available' if result['assets'] else 'empty'
            return result
        except (OSError,ValueError,KeyError,TypeError) as exc:return dict(provider=p,status='failed',error=str(exc),assets=[])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        reports=list(pool.map(one,providers))
    failed=sum(r['status']=='failed' for r in reports)
    result=dict(version='online-assets/1',status='failed' if failed==len(reports) else 'partial' if failed else 'available',
                query=query,expanded_query=expanded,filters=dict(orientation=orientation,min_width=min_width),providers=reports,assets=[a for r in reports for a in r['assets']],
                retrieval='provider keyword ranking; relevance, composition and rights require selection review',release_allowed=False)
    write(out/'results.json',result)
    cards=[]
    for a in result['assets']:
        esc=html.escape
        preview=a['preview_url']
        for manifest in sorted((CACHE/'selected').glob('*/manifest.json')):
            cached=read(manifest)
            if cached['row']['id']==a['id']:
                preview=os.path.relpath(manifest.parent/'image.png',out).replace('\\','/');break
        cards.append(f'<article><img loading="lazy" src="{esc(preview,quote=True)}"><p>{esc(a["id"])}</p><p>{esc(a["title"])}</p><p>{esc(a["creator"])} · {esc(a["license"])}</p><a href="{esc(a["source_url"],quote=True)}">来源</a></article>')
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>在线素材候选</title><style>body{font:16px system-ui;margin:40px;background:#f8f5ee}main{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}img{width:100%;height:180px;object-fit:contain}p{overflow-wrap:anywhere}</style><h1>在线素材候选：人工查看后选用</h1><p>远程预览需要联网；图片不代表本任务事实。结果文件记录接口失败。</p><main>'+''.join(cards)+'</main>',encoding='utf-8')
    return {**result,'results':str(out/'results.json'),'gallery':str(out/'index.html')}

def safe_svg(data, color):
    root=ET.fromstring(data)
    allowed={'svg','g','path','circle','ellipse','rect','line','polyline','polygon'}
    for node in root.iter():
        if node.tag.split('}')[-1] not in allowed:raise ValueError('Unsupported SVG node')
        for key,value in node.attrib.items():
            if key.lower().startswith('on') or key.split('}')[-1] in ('href','style') or re.search(r'url\s*\(',value,re.I):
                raise ValueError('Unsupported SVG reference or attribute')
    return data.decode('utf-8').replace('currentColor','#'+color).encode()

def fetch(results, asset_id, out, *, color='162E3B', node=None, sharp=None, offline=False):
    out=fresh(out);catalog=read(local(results))
    if catalog.get('version')!='online-assets/1':raise ValueError('Unsupported search results')
    row=next((r for r in catalog['assets'] if r['id']==asset_id),None)
    if not row:raise ValueError('Selected ID absent from supplied results')
    if not re.fullmatch(r'[0-9A-Fa-f]{6}',color):raise ValueError('Six-digit color required')
    provider=row['provider']
    if provider=='iconify':
        if not re.fullmatch(r'iconify:tabler:[a-z0-9-]+',asset_id) or row['license']!='MIT':raise ValueError('Only Tabler MIT icons supported')
        name=asset_id.rsplit(':',1)[1]
        url='https://api.iconify.design/tabler/'+name+'.svg'
        if row['download_url']!=url:raise ValueError('Icon URL does not match selected ID')
    elif provider in ('openverse','commons'):
        if row['license'] not in ('cc0','by') or not row.get('license_url') or not row.get('source_url'):
            raise ValueError('Supported explicit license/source required')
        if row['license']=='by' and not row.get('creator'):raise ValueError('Attribution creator missing')
        url=row['download_url']
        if provider=='commons' and urlsplit(url).hostname!='upload.wikimedia.org':raise ValueError('Unexpected Commons image host')
    else:raise ValueError('Unsupported provider')
    key=sha(json.dumps(row,sort_keys=True).encode()+color.upper().encode())
    cache=CACHE/'selected'/key;manifest=cache/'manifest.json'
    if manifest.is_file():
        record=read(manifest)
        if not record.get('files') or 'image.png' not in record['files'] or set(record['files'])-{'image.png','source.svg','LICENSE','download.bin'}:
            raise ValueError('Unsupported selected-cache file manifest')
        for name,digest in record['files'].items():
            if sha((cache/name).read_bytes())!=digest:raise ValueError('Selected cache changed')
        cache_hit=True
    else:
        if offline:raise ValueError('Selected asset is not cached')
        cache_hit=False
        data=download(url,12_000_000)
        cache.mkdir(parents=True,exist_ok=True)
        if provider=='iconify':
            if not node or not sharp:raise ValueError('SVG preparation needs explicit --node and --sharp paths')
            svg=safe_svg(data,color.upper());(cache/'source.svg').write_bytes(svg)
            js="const fs=require('fs');const sharp=require(process.argv[1]);sharp(fs.readFileSync(process.argv[2]),{density:144}).resize(512,512,{fit:'contain'}).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exitCode=1});"
            try:subprocess.run([str(node),'-e',js,str(sharp),str(cache/'source.svg'),str(cache/'image.png')],check=True,capture_output=True,timeout=30)
            except (subprocess.SubprocessError,OSError) as exc:raise RuntimeError('SVG rendering failed; check explicit Node/sharp dependencies') from exc
            shutil.copyfile(ROOT/'assets/icons/tabler-outline/LICENSE',cache/'LICENSE')
        else:
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>40_000_000 or getattr(im,'n_frames',1)>1:
                    raise ValueError('Static raster JPEG/PNG/WEBP under 40MP required')
                from PIL import ImageOps
                im=ImageOps.exif_transpose(im);im.load();im.convert('RGBA' if 'A' in im.getbands() else 'RGB').save(cache/'image.png')
            (cache/'download.bin').write_bytes(data)
        record={'row':row,'retrieved_at':datetime.now(timezone.utc).isoformat(),'download_sha256':sha(data),
                'files':{p.name:sha(p.read_bytes()) for p in cache.iterdir() if p.is_file() and p.name!='manifest.json'}}
        write(manifest,record)
    out.mkdir(parents=True)
    for name in record['files']:shutil.copyfile(cache/name,out/name)
    sid='online-'+key[:16]
    note=f'{row["title"]} — {row["creator"]} — {row["license"]} {row.get("license_version", "")} — {row["source_url"]} — {row["license_url"]}'
    (out/'attribution.txt').write_text(note,encoding='utf-8')
    result=dict(status='prepared',asset=register_asset(out/'image.png',asset_id=sid+'-asset',source_id=sid,license_note=note),
                source=dict(id=sid,kind='url',locator=row['source_url'],is_demo=False),selection=row,
                attribution=note,credit_required=row['license']=='by',cache_hit=cache_hit,cache_manifest=str(manifest),
                cache_manifest_sha256=sha(manifest.read_bytes()),editability='replaceable PNG; SVG source retained for icons, not native PPT shapes',release_allowed=False)
    write(out/'preparation.json',result)
    return {**result,'preparation':str(out/'preparation.json')}
