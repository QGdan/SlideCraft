"""Enumerate only known disposable test outputs, failed installs and duplicate environments."""
from pathlib import Path
import json,os,shutil,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'06-实施与阶段审核/最终整理-20261017'
OUT.mkdir(exist_ok=True);backup=OUT/'清理前诊断记录';backup.mkdir(exist_ok=True)
def stats(path):
    files=0;size=0;links=[];errors=[]
    for parent,dirs,names in os.walk(path,followlinks=False):
        for name in list(dirs):
            p=Path(parent)/name
            if p.is_symlink() or p.is_junction():links.append(str(p));dirs.remove(name)
        for name in names:
            try:
                f=Path(parent)/name
                if f.is_symlink():links.append(str(f));continue
                size+=f.stat().st_size;files+=1
            except OSError as exc:errors.append(str(exc))
    return {'files':files,'bytes':size,'links':links,'errors':errors}
candidates=[]
for p in sorted((ROOT/'runs').glob('p2-test-*')):
    if p.is_dir():candidates.append((p,'Repeated disposable native-content test mutations; canonical fixtures and reports retained'))
for name in ('p5-distribution-001','p5-dist-002'):
    p=ROOT/'runs'/name
    if p.exists():
        candidates.append((p,'Superseded failed distribution/install; final approved ZIP and successful evidence retained'))
        for r in p.rglob('installation.json'):
            if '.venv' not in r.parts and '.mcp-venv' not in r.parts:shutil.copy2(r,backup/(name+'-installation.json'))
for folder in ('p5-dist-003','p5-reinstall-004'):
    for name in ('.venv','.mcp-venv','node_modules','.npm','.tmp'):
        p=ROOT/'runs'/folder/'ppt-workflow'/name
        if p.exists():candidates.append((p,'Duplicate installation environment; source, generated decks, logs, vendor and final ZIP retained'))
p=ROOT/'experiments/p4/npm-cache'
if p.exists():candidates.append((p,'Disposable npm download cache; isolated automizer installation and lockfile retained'))
rows=[]
for p,reason in candidates:
    target=p.resolve()
    if not target.is_relative_to(ROOT) or target in [ROOT,ROOT/'.venv',ROOT/'.mcp-venv',ROOT/'node_modules']:raise ValueError('Unsafe cleanup candidate')
    record={'path':str(target),'relative':target.relative_to(ROOT).as_posix(),'reason':reason,**stats(target)}
    record['eligible']=not record['links'] and not record['errors'];rows.append(record)
plan={'authorization':'User requested cleanup of unused workflow artifacts on 2026-10-17','root':str(ROOT),
    'preserved':['active .venv/.mcp-venv/node_modules','all P0–P5 audit directories and ZIPs','54 historical originals','templates/assets','canonical test fixtures','P4 installed automizer','P5 successful generated PPTs/logs/vendor'],
    'candidates':rows,'eligible_count':sum(r['eligible'] for r in rows),'eligible_bytes':sum(r['bytes'] for r in rows if r['eligible'])}
(OUT/'清理计划.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'candidates':len(rows),'eligible_count':plan['eligible_count'],'bytes':plan['eligible_bytes'],
    'largest':sorted([{'path':r['relative'],'MiB':round(r['bytes']/1048576,2)} for r in rows],key=lambda x:x['MiB'],reverse=True)[:12]},ensure_ascii=False))
