"""Freeze P1 tests, known probes and real-render bindings for stage review."""
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.qa.inspect import inspect_deck,bind_render
from ppt_workflow.contracts import validate
from ppt_workflow.render import sha256

P1=ROOT.parent/"06-实施与阶段审核/P1"
P1.mkdir(parents=True,exist_ok=True)

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

tests=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
save(P1/"tests.json",{"returncode":tests.returncode,"stdout":tests.stdout,"stderr":tests.stderr})
print(tests.stderr)
if tests.returncode:raise SystemExit(tests.returncode)
records=[]
folder=ROOT.parent/"05-开源项目深度研究/本地核查证据"
for filename in ["nontext_offslide.pptx","group_offslide.pptx","unbroken_long_word.pptx","inherited_background.pptx","undeclared_axis_validator_probe.zip"]:
    report=inspect_deck(folder/filename)
    errors=validate(report.qa,"qa")
    if errors:raise RuntimeError(errors)
    records.append({"file":filename,"status":report.qa["status"],"rules":sorted({i["rule"] for i in report.qa["issues"]}),"exceptions":[u for u in report.qa["coverage"]["unknown"] if "exception" in u]})
save(P1/"original-probes-v2.json",records)
binding=[]
for label,deck,render in [
    ("baseline",ROOT/"runs/p0-20261014-001/rebuild/demo-zh.pptx",ROOT/"runs/p1-real-render-001/render-manifest.json"),
    ("native-text-probe",ROOT/"runs/p1-real-probe/probe.pptx",ROOT/"runs/p1-real-probe/render/render-manifest.json")]:
    manifest=json.loads(render.read_text(encoding="utf-8"))
    inspection=bind_render(inspect_deck(deck),manifest)
    if validate(inspection.qa,"qa"):raise RuntimeError("Invalid final QA report")
    save(P1/(label+"-qa.json"),inspection.qa)
    save(P1/(label+"-details.json"),inspection.details)
    binding.append({"label":label,"qa_status":inspection.qa["status"],"render_status":manifest["status"],"images":len(manifest["images"]),"target_bounds":len(inspection.details.get("target_bounds",[])),"error_rules":sorted({i["rule"] for i in inspection.qa["issues"] if i["severity"]=="error"})})
baseline_manifest=json.loads((ROOT.parent/"06-实施与阶段审核/P0/baseline-manifest.json").read_text(encoding="utf-8"))
changed=[r["path"] for r in baseline_manifest["originals"] if sha256(ROOT.parent/r["path"])!=r["sha256"]]
sources=[]
for directory in ["ppt_workflow","tests","schemas","render","scripts"]:
    for path in sorted((ROOT/directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            sources.append({"path":path.relative_to(ROOT).as_posix(),"sha256":sha256(path)})
qa_runs=sorted((ROOT/"runs").glob("p1-qa-tests-*"),key=lambda p:p.stat().st_mtime)
render_runs=sorted((ROOT/"runs").glob("p1-render-tests-*"),key=lambda p:p.stat().st_mtime)
fixtures=json.loads((qa_runs[-1]/"fixture-results.json").read_text(encoding="utf-8"))
mock_results=json.loads((render_runs[-1]/"test-results.json").read_text(encoding="utf-8"))
summary={"created_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"tests_passed":True,"fixture_dir":str(qa_runs[-1]),"render_test_dir":str(render_runs[-1]),"fixture_variant_count":len(fixtures),"mock_renderer_results":mock_results,"real_renders":binding,"original_files_changed":changed,"source_hashes":sources,"stage_status":"awaiting_user_review"}
save(P1/"verification.json",summary)
print(json.dumps({"tests_passed":True,"real_renders":binding,"original_files_changed":changed},ensure_ascii=False))
if changed:raise SystemExit(1)
