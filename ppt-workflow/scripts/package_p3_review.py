"""Snapshot a G3 review candidate; deliberately does not call it a release."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.workflow import read, write, sha256, load_job, verify_evidence

stage = ROOT.parent / '06-实施与阶段审核/P3'
run, state, revision = load_job(ROOT / 'runs/p3-unified-cli-003')
verify_evidence(state)
assert state['status'] == 'unverified'
qa_dir = Path(state['qa_directory'])
qa = read(qa_dir / 'qa.json')
assert not qa['issues'] and qa['stages']['visual']['status'] == 'passed'
assert qa['stages']['render']['status'] == qa['stages']['content']['status'] == 'passed'
assert qa['coverage']['unknown'] and qa['status'] == 'unverified'
probes = read(ROOT / 'runs/p3-size-probes/results.json')
assert [p['requested'] for p in probes] == [8,20]
assert all(p['requested'] == p['office_count'] == p['render_count'] for p in probes)
test_log = (ROOT / 'runs/p3-tests-final.log').read_text(encoding='utf-8-sig')
match = re.search(r'Ran (\d+) tests', test_log)
assert match and 'OK' in test_log[-100:] and 'FAILED' not in test_log
baseline = read(ROOT.parent / '06-实施与阶段审核/P0/baseline-manifest.json')
assert all(sha256(ROOT.parent / row['path']) == row['sha256'] for row in baseline['originals'])

out = stage / '审核包'
out.mkdir(exist_ok=False)
shutil.copy2(revision / 'deck.pptx', out / '候选稿-教学报告.pptx')
shutil.copy2(revision / 'contact.png', out / '十页接触表.png')
for name in ('deck-spec.json','brief.json'):
    shutil.copy2(revision / name, out / name)
shutil.copytree(qa_dir, out / 'review')
shutil.copytree(revision / 'render-000/slides', out / 'slides')
shutil.copy2(revision / 'render-000/powerpoint-worker.json', out / 'render-worker.json')
shutil.copytree(Path(state['build_attempt']) / 'office', out / 'office-evidence')
for name in ('state.json','inputs.json','outline.json','config.json','host-review.json'):
    shutil.copy2(run / name, out / name)
shutil.copy2(ROOT / 'runs/p3-tests-final.log', out / 'tests.log')
shutil.copytree(ROOT / 'skills/ppt-quality-workflow', out / 'ppt-quality-workflow')
snapshot = out / 'code-snapshot'
for folder, pattern in [('ppt_workflow','*.py'),('engine','*.cjs'),('office-mcp','*.py'),('render','*.ps1'),('schemas','*.json'),('templates','*.json'),('scripts','*.py')]:
    for src in (ROOT / folder).rglob(pattern):
        target = snapshot / src.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,target)
for name in ('package.json','package-lock.json','requirements.lock.txt','office-mcp/requirements.lock.txt','examples/workflow-unified.json','README.md'):
    target = snapshot / name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT / name,target)
for folder in ('assets/unified-v3',):
    shutil.copytree(ROOT / folder, out / folder)
shutil.copy2(ROOT / 'runs/p2-unified-template-003/Unified-Ivory.potx', out / '统一暖白青绿模板.potx')
shutil.copy2(ROOT / 'examples/demo-report-v1.json', out / '事实来源-示意.json')
shutil.copy2(ROOT / 'runs/p3-size-probes/results.json', out / 'size-probes.json')
for name in ('最终运行',): shutil.copytree(stage / name, out / name)
shutil.copy2(stage / 'P3阶段审核.md', out / 'P3阶段审核.md')
verification = {'purpose':'G3-review-candidate-not-a-release','unit_tests':int(match.group(1)),'test_failures':0,
                'original_hashes_unchanged':len(baseline['originals']),'qa_status':qa['status'],'visual_status':qa['stages']['visual']['status'],
                'remaining_unknown':len(qa['coverage']['unknown']),'main_slide_count':10,'size_probes':probes,
                'input_digest':state['input_digest'],'deck_sha256':state['deck_sha256'],'figma_roundtrip':'not-verified',
                'global_skill_installation':'not-performed'}
write(out / 'verification.json', verification)
records = [{'path':str(p.relative_to(out)),'sha256':sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()]
write(out / 'manifest.json',{'purpose':'stage-review-not-release','files':records})
with ZipFile(stage / 'P3-阶段审核包.zip','w',ZIP_DEFLATED) as archive:
    for p in sorted(out.rglob('*')):
        if p.is_file(): archive.write(p,str(p.relative_to(out)))
assert all(sha256(out / r['path']) == r['sha256'] for r in records)
with ZipFile(stage / 'P3-阶段审核包.zip') as archive: assert archive.testzip() is None
write(stage / 'verification.json',{**verification,'review_zip_sha256':sha256(stage / 'P3-阶段审核包.zip'),'file_count':len(records)})
print(json.dumps(verification,ensure_ascii=False,indent=2))
