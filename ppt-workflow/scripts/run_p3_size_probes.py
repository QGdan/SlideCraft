"""Mechanical 8/20-page probes, explicitly not approved presentation content."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.workflow import read, write, sha256
from ppt_workflow.unified import PROFILE

out = ROOT / 'runs/p3-size-probes'
out.mkdir(exist_ok=False)
original = read(ROOT / 'runs/p2-unified-content-003/deck-spec.json')
brief = read(ROOT / 'runs/p2-unified-content-003/brief.json')
template = ROOT / 'runs/p2-unified-template-003/Unified-Ivory.potx'
results = []
for count in (8, 20):
    deck = deepcopy(original)
    deck['job_id'] = f'p3-size-probe-{count}'
    deck['slides'] = [deepcopy(original['slides'][i % 10]) for i in range(count)]
    for i, page in enumerate(deck['slides'], 1):
        page['id'] = f's{i:02d}'
        for j, element in enumerate(page['elements'], 1):
            element['id'] = f's{i:02d}-e{j:02d}'
            if element['type'] == 'text' and element['rect'] == dict(zip(('x','y','w','h'), read(PROFILE)['regions']['page'])):
                element['text'] = f'{i:02d}'
            if element['type'] == 'text' and element['role'] == 'caption':
                element['text'] = f'{count} 页功能探针 · 非正式演示'
    spec_path, brief_path = out / f'spec-{count}.json', out / f'brief-{count}.json'
    write(spec_path, deck); write(brief_path, {**brief, 'job_id': deck['job_id'], 'slide_count': count})
    config = {'brief': str(brief_path), 'spec': str(spec_path), 'template': str(template), 'design_system': str(PROFILE),
              'node': 'D:/node/node.exe', 'renderer': 'powerpoint', 'design_approval': {
                  'spec_sha256': sha256(spec_path), 'template_sha256': sha256(template), 'design_sha256': sha256(PROFILE),
                  'reviewer': 'agent-functional-probe', 'evidence': 'User authorized P3 implementation/testing; this is a mechanical probe, not user approval of new presentation content.'}}
    config_path = out / f'config-{count}.json'; write(config_path, config)
    run = out / f'job-{count}'
    for step, argv, expected in [('plan', ['plan','--config',config_path,'--out',run],0),
                                 ('build-qa',['build','--run',run,'--with-qa'],2)]:
        proc = subprocess.run([sys.executable,'-m','ppt_workflow',*map(str,argv)], cwd=ROOT, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=210)
        write(out / f'{count}-{step}.json', {'returncode': proc.returncode, 'expected': expected, 'stdout': proc.stdout, 'stderr': proc.stderr})
        if proc.returncode != expected: raise RuntimeError(f'{count} {step}: unexpected exit {proc.returncode}')
    state = read(run / 'state.json')
    render = read(Path(state['qa_directory']) / 'render-manifest.json')
    worker = read(Path(state['build_attempt']) / 'office/office-worker.json')
    assert worker['slide_count'] == len(worker['slide_layouts']) == len(render['images']) == count
    results.append({'requested':count,'office_count':worker['slide_count'],'render_count':len(render['images']),
                    'qa_status':state['qa_status'],'status':'mechanical-probe-passed','content_approval':'not-a-production-deck'})
    write(out / 'results.json', results)
    print(f'{count} pages: Office count and rendered PNG count verified',flush=True)
