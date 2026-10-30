"""Audit the decoupled skills without pretending the CLI performs agent work."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ppt_workflow.workflow import read,write,sha256
from ppt_workflow.stages import registry

out=ROOT.parent/'06-实施与阶段审核/P3-Skill解耦修订'
out.mkdir(exist_ok=True)
proof=out/'命令演示';proof.mkdir(exist_ok=False)
workspace=ROOT/'runs/p3-decoupled-cli-001'
calls=[]
def invoke(name,argv,expected):
    p=subprocess.run([sys.executable,'-m','ppt_workflow',*map(str,argv)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    write(proof/(name+'.json'),{'command':argv,'returncode':p.returncode,'expected':expected,'stdout':p.stdout,'stderr':p.stderr})
    assert p.returncode==expected,(name,p.stdout,p.stderr)
    calls.append({'name':name,'exit':p.returncode,'expected':expected})
    return json.loads(p.stdout)
invoke('skills',['skills'],0)
invoke('doctor',['doctor'],0)
for item in registry()['stages']:
    invoke('route-'+item['command'],[item['command'],'--workspace',str(workspace)],2 if item['command']=='intake' else 1)
example=out/'未完成需求-仅命令演示.json'
write(example,{'topic':'Skill 解耦交接演示','audience':'','goal':'验证需求未补齐不能跳过','language':'zh-CN',
               'delivery_mode':'presented','slide_count':10,'aspect_ratio':'16:9','brand':'沿用项目统一模板',
               'editability':'原生文字与数据对象','open_questions':[{'question':'TEST ONLY: audience is intentionally unspecified','required':True,'answer':None}]})
pending=invoke('intake-needs-input',['intake','--workspace',str(workspace),'--input',str(example)],2)
invoke('outline-gate',['outline','--workspace',str(workspace),'--input',str(example)],1)
invoke('incomplete-approval-rejected',['intake','--workspace',str(workspace),'--approve',pending['artifact_sha256'],
                                     '--reviewer','TEST ONLY','--evidence','Negative test; this must be rejected'],1)
assert not list(workspace.rglob('approval.json'))
write(proof/'commands.json',calls)
installed=ROOT/'runs/p3-decoupled-installed-001'
p=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--dest',str(installed),'--apply'],capture_output=True,text=True,encoding='utf-8')
assert p.returncode==0,p.stderr
write(proof/'project-local-install.json',json.loads(p.stdout))
checks=[]
validator=Path.home()/'.codex/skills/.system/skill-creator/scripts/quick_validate.py'
for folder in sorted((ROOT/'skills').iterdir()):
    if not (folder/'SKILL.md').is_file():continue
    p=subprocess.run(['D:/Python/python.exe','-X','utf8',str(validator),str(folder)],capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==0,(folder,p.stdout,p.stderr)
    checks.append({'skill':folder.name,'returncode':p.returncode,'message':p.stdout.strip()})
    for source in folder.rglob('*'):
        if source.is_file() and source.name!='runtime.json':
            assert sha256(source)==sha256(installed/folder.name/source.relative_to(folder))
    assert read(installed/folder.name/'runtime.json')['project_root']==str(ROOT)
write(out/'skill-validation.json',checks)
log=(ROOT/'runs/p3-decoupled-tests.log').read_text(encoding='utf-8-sig')
match=re.search(r'Ran (\d+) tests',log)
assert match and 'OK' in log[-100:] and 'FAILED' not in log
shutil.copy2(ROOT/'runs/p3-decoupled-tests.log',out/'tests.log')
shutil.copytree(ROOT/'skills',out/'skills')
snapshot=out/'code-snapshot'
for name in ['ppt_workflow/stages.py','ppt_workflow/__main__.py','ppt_workflow/workflow.py','skill-routing.json',
             'scripts/install_skill.py','scripts/package_stage_skills.py','tests/test_stages.py','README.md']:
    target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
baseline=read(ROOT.parent/'06-实施与阶段审核/P0/baseline-manifest.json')
assert all(sha256(ROOT.parent/r['path'])==r['sha256'] for r in baseline['originals'])
write(out/'verification.json',{'purpose':'G3-skill-decoupling-review','skills':len(checks),'stage_skills':6,
      'tests':int(match.group(1)),'test_failures':0,'original_hashes_unchanged':len(baseline['originals']),
      'global_installation':False,'new_presentation_created':False,'cli_invokes_language_model':False,
      'complete_chain_test':'isolated fixtures explicitly marked TEST ONLY; no real approvals forged',
      'cli_demo':'incomplete requirement persisted; downstream and premature approval rejected'})
records=[{'path':str(p.relative_to(out)),'sha256':sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()]
write(out/'manifest.json',{'files':records,'purpose':'stage-review-not-a-production-release'})
archive_path=out.parent/'P3-Skill解耦审核包.zip'
with ZipFile(archive_path,'w',ZIP_DEFLATED) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(out)))
with ZipFile(archive_path) as z:assert z.testzip() is None
assert all(sha256(out/r['path'])==r['sha256'] for r in records)
print(json.dumps({'skills':len(checks),'tests':int(match.group(1)),'file_count':len(records),'zip_sha256':sha256(archive_path)},ensure_ascii=False))
