"""Repeatable engineering checkpoints; never authors/reviews a business deck."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--node',type=Path,required=True);a=p.parse_args()
out=a.out.resolve()
if not out.is_relative_to(ROOT.parent) or out.exists():raise SystemExit('Fresh project-local evidence directory required')
out.mkdir(parents=True)
quality_output=ROOT/'runs'/('engineering-'+hashlib.sha256(str(out).encode('utf-8')).hexdigest()[:12])/'quality-command'
env={**os.environ,'PPT_WORKFLOW_NODE':str(a.node.resolve()),'PYTHONUTF8':'1'}
steps=[('full-regression',[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-v'],0,300),
       ('capabilities',[sys.executable,'-X','utf8','-m','ppt_workflow','capabilities'],0,20),
       ('quality-command',[sys.executable,'-X','utf8','-m','ppt_workflow','quality-check','--outline','examples/quality-outline.json','--plan','examples/content-plan.json','--out',str(quality_output)],2,20),
       ('portable-smoke',[sys.executable,'-X','utf8','scripts/smoke.py','--node',str(a.node.resolve())],0,180)]
records=[]
for name,cmd,expected,timeout in steps:
    start=time.perf_counter()
    try:
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        log=out/f'{name}.log';log.write_text(r.stdout+r.stderr,encoding='utf-8')
        ok=r.returncode==expected
        if name=='quality-command' and ok:
            payload=json.loads(r.stdout);ok=payload['automated_checks_passed'] and payload['status']=='needs_review' and payload['release_allowed'] is False
        records.append({'step':name,'command':cmd,'expected_exit':expected,'exit_code':r.returncode,'passed':ok,'elapsed_seconds':round(time.perf_counter()-start,3),
            'log':str(log),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
    except subprocess.TimeoutExpired:
        records.append({'step':name,'passed':False,'error':'timeout','seconds':timeout})
    (out/'verification.json').write_text(json.dumps({'scope':'Engineering checks, not visual acceptance or live Office certification','steps':records,'passed':len(records)==len(steps) and all(x['passed'] for x in records)},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(records[-1],ensure_ascii=False),flush=True)
    if not records[-1]['passed']:raise SystemExit(1)
