"""Route and installation probes, with no synthetic human approval records."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];RUNTIME=Path(sys.argv[1]).resolve();PY=RUNTIME/'.venv/Scripts/python.exe'
OUT=RUNTIME/'runs/p5-cli-smoke';OUT.mkdir(exist_ok=False)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
records=[]
def call(label,argv,expected):
    p=subprocess.run(list(map(str,argv)),cwd=RUNTIME,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    record={'name':label,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'expected':expected}
    records.append(record);save(OUT/'results.json',records)
    assert p.returncode==expected,record
    return json.loads(p.stdout)
call('doctor',[PY,'-m','ppt_workflow','doctor'],0)
registry=call('skills',[PY,'-m','ppt_workflow','skills'],0)
for stage in registry['stages']:
    path=Path(stage['route']['path']);assert path.is_relative_to(RUNTIME) and path.is_file()
    command=stage['command']
    call(command,[PY,'-m','ppt_workflow',command,'--workspace',OUT/'handoffs'],2 if command=='intake' else 1)
call('local-install',[PY,RUNTIME/'scripts/install_skill.py','--dest',OUT/'installed','--apply'],0)
# Refusal writes a plain message to stderr, so do not parse this negative result as JSON.
p=subprocess.run([str(PY),str(RUNTIME/'scripts/install_skill.py'),'--dest',str(OUT/'installed'),'--apply'],cwd=RUNTIME,capture_output=True,text=True,encoding='utf-8',timeout=20)
assert p.returncode==1 and 'already exists' in p.stderr
save(OUT/'reinstall-refused.json',{'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
for name in ['ppt-quality-workflow']+[s['skill'] for s in registry['stages']]:
    binding=json.loads((OUT/'installed'/name/'runtime.json').read_text(encoding='utf-8'))
    assert Path(binding['project_root'])==RUNTIME
assert not list((OUT/'handoffs').rglob('approval.json'))
print(json.dumps({'status':'passed','routes':6,'installed':7,'reinstall':'refused','human_approvals_created':0}))
