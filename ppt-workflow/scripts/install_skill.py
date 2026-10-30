"""Prepare or install a project-bound skill; never replace an existing skill."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

parser = argparse.ArgumentParser()
parser.add_argument('--dest', type=Path, required=True, help='Explicit skill parent directory')
parser.add_argument('--apply', action='store_true', help='Copy into a fresh destination; default only previews')
registry = json.loads((ROOT / 'skill-routing.json').read_text(encoding='utf-8'))
names = ['ppt-quality-workflow'] + [s['skill'] for s in registry['stages']]
parser.add_argument('--skill', action='append', choices=['all', *names], help='Select independent skills; default installs the suite')
args = parser.parse_args()
selected = names if not args.skill or 'all' in args.skill else list(dict.fromkeys(args.skill))
targets = [(ROOT / 'skills' / name, args.dest.resolve() / name) for name in selected]
if any(target.exists() for source, target in targets):
    raise SystemExit('A destination already exists; no existing skill was changed and no partial suite was installed')
if any(not (source / 'SKILL.md').is_file() for source, target in targets):
    raise SystemExit('A selected skill source is unavailable')
if args.apply:
    for source, target in targets:
        shutil.copytree(source, target)
        (target / 'runtime.json').write_text(json.dumps({'project_root': str(ROOT), 'binding': 'project-local-runtime', 'skill': source.name}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': 'installed' if args.apply else 'preview', 'project': str(ROOT),
                  'skills': [{'skill': source.name, 'destination': str(target)} for source, target in targets],
                  'configuration_files_changed': False}, ensure_ascii=False))
