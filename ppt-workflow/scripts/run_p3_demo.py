"""Real CLI demonstration. No automated review or release approval is fabricated."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.workflow import read, write

parser = argparse.ArgumentParser()
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
run, out = args.run.resolve(), args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
records = []

def invoke(name, arguments, expected):
    argv = [sys.executable, '-m', 'ppt_workflow', *map(str, arguments)]
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=210)
    result = {'name': name, 'command': argv, 'returncode': proc.returncode, 'expected_returncode': expected,
              'stdout': proc.stdout, 'stderr': proc.stderr}
    write(out / (name + '.json'), result)
    records.append({'name': name, 'returncode': proc.returncode, 'expected': expected})
    write(out / 'commands.json', records)
    if proc.returncode != expected:
        raise RuntimeError(f'{name} returned {proc.returncode}; expected {expected}; see output log')
    print(name + ': exit ' + str(proc.returncode), flush=True)
    return json.loads(proc.stdout)

invoke('doctor', ['doctor'], 0)
invoke('plan', ['plan', '--config', ROOT / 'examples/workflow-unified.json', '--out', run], 0)
invoke('build-and-qa', ['build', '--run', run, '--with-qa'], 2)
invoke('resume', ['build', '--run', run, '--resume'], 2)
invoke('deliver-blocked', ['deliver', '--run', run, '--out', run.parent / (run.name + '-release')], 1)
invoke('benchmark', ['benchmark', '--runs', run], 0)

source = read(ROOT / 'examples/workflow-unified.json')
# The demonstration copy uses absolute paths so only the intended condition varies.
for field in ('spec', 'brief', 'template', 'design_system'):
    source[field] = str((ROOT / 'examples' / source[field]).resolve())
inputs = run.parent / (run.name + '-demonstrations')
inputs.mkdir()
bad = {**source, 'design_approval': {}}
write(inputs / 'unapproved.json', bad)
invoke('unapproved-plan-blocked', ['plan', '--config', inputs / 'unapproved.json', '--out', inputs / 'unapproved-job'], 1)
write(inputs / 'changed-input.json', source)
invoke('invalidation-plan', ['plan', '--config', inputs / 'changed-input.json', '--out', inputs / 'changed-job'], 0)
source['demonstration_note'] = 'This config changed after approval was bound.'
write(inputs / 'changed-input.json', source)
invoke('changed-input-blocked', ['build', '--run', inputs / 'changed-job', '--resume'], 1)
print('Real demonstration complete; candidate still needs review; no release created.', flush=True)
