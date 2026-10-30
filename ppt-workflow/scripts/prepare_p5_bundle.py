"""Prepare a relocatable candidate; dependencies come only from recorded exact URLs."""
from pathlib import Path
import sys,json,hashlib,shutil,urllib.request,base64,argparse
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ppt_workflow.workflow import read,write,sha256
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'runs/p5-dist-003');a=p.parse_args()
OUT=a.out.resolve()
if not OUT.is_relative_to(ROOT/'runs'):raise ValueError('Distribution staging must stay inside runs')
OUT.mkdir(exist_ok=False)
runtime=OUT/'ppt-workflow';runtime.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc')
for folder in ('ppt_workflow','engine','render','schemas','skills','templates','assets','examples','office-mcp','tests'):
    shutil.copytree(ROOT/folder,runtime/folder,ignore=ignore)
scripts=runtime/'scripts';scripts.mkdir()
for name in ('bootstrap.py','create_demo.py','install_skill.py','office_mcp_client.py'):
    shutil.copy2(ROOT/'scripts'/name,scripts/name)
for name in ('README.md','requirements.lock.txt','requirements.in','package.json','package-lock.json','skill-routing.json','THIRD_PARTY_NOTICES.md','pip-install-report.json','office-mcp-install-report.json'):
    shutil.copy2(ROOT/name,runtime/name)
shutil.copy2(ROOT/'runs/p2-unified-template-003/Unified-Ivory.potx',runtime/'templates/unified-v3/Unified-Ivory.potx')
(runtime/'runs').mkdir()
vendor=runtime/'vendor';(vendor/'wheels').mkdir(parents=True)
wheel_records={};group_locks={}
for label,report,lock in [('runtime','pip-install-report.json','requirements.lock.txt'),('office','office-mcp-install-report.json','office-mcp/requirements.lock.txt')]:
    report=read(ROOT/report)
    installed={r['metadata']['name'].lower().replace('_','-'):r for r in report['install']}
    lines=[]
    for line in (ROOT/lock).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        name,version=line.split('==');r=installed[name.lower().replace('_','-')]
        assert r['metadata']['version']==version
        info=r['download_info'];url=info['url'];expected=info['archive_info']['hashes']['sha256']
        assert url.startswith('https://files.pythonhosted.org/') and url.endswith('.whl')
        file=url.rsplit('/',1)[1];wheel_records[file]={'url':url,'sha256':expected,'path':f'vendor/wheels/{file}'}
        lines.append(f'{line} --hash=sha256:{expected}')
    target=vendor/f'{label}.lock.txt';target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def download(item):
    name,r=item;target=runtime/r['path']
    cached=ROOT/'runs/p5-distribution-001/ppt-workflow'/r['path']
    if cached.is_file() and sha256(cached)==r['sha256']:data=cached.read_bytes()
    else:
        with urllib.request.urlopen(r['url'],timeout=50) as response:data=response.read()
    if hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('Wheel hash mismatch: '+name)
    target.write_bytes(data);return {'file':name,'bytes':len(data),**r}
with ThreadPoolExecutor(max_workers=4) as pool:downloads=list(pool.map(download,wheel_records.items()))
write(vendor/'wheel-sources.json',downloads)
tarballs=vendor/'npm-tarballs';tarballs.mkdir();npm_sources=[]
for name,meta in read(ROOT/'package-lock.json')['packages'].items():
    if not name:continue
    algo,encoded=meta['integrity'].split('-',1);assert algo=='sha512'
    hexsum=base64.b64decode(encoded).hex()
    cache=ROOT/'.npm-cache/_cacache/content-v2/sha512'/hexsum[:2]/hexsum[2:4]/hexsum[4:]
    data=cache.read_bytes()
    assert hashlib.sha512(data).hexdigest()==hexsum
    target=tarballs/(hexsum[:20]+'.tgz');target.write_bytes(data)
    npm_sources.append({'package':name,'version':meta['version'],'url':meta['resolved'],
        'integrity':meta['integrity'],'path':target.relative_to(runtime).as_posix(),'sha256':sha256(target)})
write(vendor/'npm-sources.json',npm_sources)
records=[{'path':p.relative_to(runtime).as_posix(),'sha256':sha256(p)} for p in sorted(vendor.rglob('*')) if p.is_file()]
write(vendor/'manifest.json',records)
write(OUT/'preparation.json',{'runtime':str(runtime),'wheel_count':len(downloads),'downloaded_bytes':sum(r['bytes'] for r in downloads),
    'npm_cache':'verified exact tarballs; bootstrap seeds a fresh cache and runs npm ci --offline',
    'status':'prepared-not-yet-installed','third_party_fonts_or_office_binaries_included':False})
print(json.dumps(read(OUT/'preparation.json'),ensure_ascii=False))
