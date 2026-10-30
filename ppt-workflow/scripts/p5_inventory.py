"""Collect installed metadata and license files for the local candidate, no license inference."""
from pathlib import Path
import json,hashlib,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
runtime=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve();dest.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
report=json.loads((runtime/'vendor/wheel-sources.json').read_text(encoding='utf-8'))
code='''import importlib.metadata as m,json
print(json.dumps([{'name':d.metadata['Name'],'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license':d.metadata.get('License'),'project_urls':d.metadata.get_all('Project-URL'),'files':[str(d.locate_file(f)) for f in d.files or [] if '.dist-info/' in str(f) and any(k in str(f).lower() for k in ['license','copying','notice'])]} for d in m.distributions() if d.metadata['Name']!='pip']))'''
proc=subprocess.run([str(runtime/'.mcp-venv/Scripts/python.exe'),'-X','utf8','-c',code],capture_output=True,text=True,encoding='utf-8',check=True)
python=json.loads(proc.stdout)
for r in python:
    folder=dest/'python'/(r['name']+'-'+r['version']);folder.mkdir(parents=True)
    licenses=[]
    for n,f in enumerate(r.pop('files'),1):
        p=Path(f)
        if not p.is_file():continue
        q=folder/f'{n:02d}-{p.name}';shutil.copy2(p,q)
        licenses.append({'path':q.relative_to(dest).as_posix(),'sha256':sha(q)})
    r['license_files']=licenses
nodes=[]
lock=json.loads((runtime/'package-lock.json').read_text(encoding='utf-8'))
for path,meta in lock['packages'].items():
    if not path:continue
    folder=runtime/path;package=json.loads((folder/'package.json').read_text(encoding='utf-8'))
    target=dest/'node'/package['name'].replace('/','_');target.mkdir(parents=True)
    files=[]
    for f in folder.iterdir():
        if f.is_file() and f.name.lower().startswith(('license','licence','copying','notice')):
            q=target/f.name;shutil.copy2(f,q);files.append({'path':q.relative_to(dest).as_posix(),'sha256':sha(q)})
    if not files:
        for f in folder.glob('README*'):
            if '## License' in f.read_text(encoding='utf-8',errors='replace'):
                q=target/f.name;shutil.copy2(f,q);files.append({'path':q.relative_to(dest).as_posix(),'sha256':sha(q),'license_embedded_in_readme':True})
    nodes.append({'name':package['name'],'version':package['version'],'license':package.get('license'),
        'resolved':meta['resolved'],'integrity':meta['integrity'],'license_files':files})
assets=[]
for f in (runtime/'assets').rglob('*.png'):
    assets.append({'path':f.relative_to(runtime).as_posix(),'sha256':sha(f),'origin':'user-authorized image generation/edit; see adjacent prompts.json',
        'permission_scope':'local project and review candidate; not a claim of public redistribution clearance or vector editability'})
save(dest/'dependency-inventory.json',{'python':python,'node':nodes,'assets':assets,
    'python_source_records':report,'not_bundled':['PowerPoint','Windows fonts','Python runtime','Node runtime'],
    'project_source_license':'No public release license assigned; local user-owned research candidate only',
    'missing_license_files':[r['name'] for r in python+nodes if not r['license_files']]})
print(json.dumps({'python':len(python),'node':len(nodes),'assets':len(assets),'missing_license_files':[r['name'] for r in python+nodes if not r['license_files']]},ensure_ascii=False))
