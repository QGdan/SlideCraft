"""Second installation from the final ZIP at a different path, with real Office smoke."""
from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'runs/p5-reinstall-004/ppt-workflow'
OUT=ROOT/'runs/p5-final-repro';OUT.mkdir(exist_ok=False);records=[]
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def run(name,argv,expected,timeout=180):
    t=time.perf_counter();p=subprocess.run(list(map(str,argv)),cwd=RUNTIME,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    row={'name':name,'command':list(map(str,argv)),'exit':p.returncode,'expected':expected,'seconds':round(time.perf_counter()-t,3),'stdout':p.stdout,'stderr':p.stderr}
    records.append(row);save(OUT/'commands.json',records)
    print(f'{name}: {p.returncode} (expected {expected})',flush=True)
    if p.returncode!=expected:raise RuntimeError(p.stdout+p.stderr)
node='D:/node/node.exe';py=RUNTIME/'.venv/Scripts/python.exe'
run('bootstrap',['D:/Python/python.exe','-X','utf8','scripts/bootstrap.py','--node',node,'--apply'],0,240)
run('portable-tests',[py,'-X','utf8','scripts/smoke.py','--node',node],0)
run('doctor',[py,'-X','utf8','-m','ppt_workflow','doctor'],0)
run('create-demo',[py,'-X','utf8','scripts/create_demo.py','--node',node,'--out','examples/final-demo'],0)
run('plan',[py,'-X','utf8','-m','ppt_workflow','plan','--config','examples/final-demo/workflow.json','--out','runs/final-demo'],0)
run('build-qa',[py,'-X','utf8','-m','ppt_workflow','build','--run','runs/final-demo','--with-qa'],2)
run('deny-unverified-release',[py,'-X','utf8','-m','ppt_workflow','deliver','--run','runs/final-demo','--out','runs/final-demo/must-not-release'],1)
assert not (RUNTIME/'runs/final-demo/must-not-release').exists()
state=json.loads((RUNTIME/'runs/final-demo/state.json').read_text(encoding='utf-8'))
q=Path(state['qa_directory']);qa=json.loads((q/'qa.json').read_text(encoding='utf-8'));render=json.loads((q/'render-manifest.json').read_text(encoding='utf-8'))
save(OUT/'verification.json',{'status':'installation-and-mechanical-smoke-passed','runtime':str(RUNTIME),'portable_tests':77,
    'rendered_pages':len(render['images']),'render_status':render['status'],'qa_status':qa['status'],'formal_delivery':'correctly-rejected',
    'errors':sum(i['severity']=='error' for i in qa['issues']),'unknown':len(qa['coverage']['unknown']),
    'platform_scope':'Same physical Windows host, new paths and new Python/Node dependency environments; not a clean OS or second machine test.'})
