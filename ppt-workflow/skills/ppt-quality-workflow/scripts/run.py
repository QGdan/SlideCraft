"""Thin launcher; production modules stay in the bound project."""
import json
from pathlib import Path
import subprocess
import sys

folder = Path(__file__).resolve().parents[1]
runtime = json.loads((folder / 'runtime.json').read_text(encoding='utf-8'))
project = (folder / runtime['project_root']).resolve()
python = project / '.venv/Scripts/python.exe'
if not python.is_file() or not (project / 'ppt_workflow/workflow.py').is_file():
    raise SystemExit('Bound project runtime is unavailable; restore it before using this skill')
raise SystemExit(subprocess.run([str(python), '-m', 'ppt_workflow', *sys.argv[1:]], cwd=project).returncode)
