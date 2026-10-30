"""Stage-specific sample builder; production orchestration belongs to P3."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.design import demo_deck,THEMES
from ppt_workflow.contracts import validate,validate_bundle
from ppt_workflow.content import check_ledger,inspect_native,bind_content
from ppt_workflow.export_fix import normalize
from ppt_workflow.qa.inspect import inspect_deck


def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def build(out, theme):
    out.mkdir(parents=True,exist_ok=False)
    deck,t=demo_deck(theme)
    brief=dict(schema_version="0.1",job_id=deck["job_id"],topic="教学报告自动化试点方案",audience="教研组与信息化团队",
               language="zh-CN",delivery_mode="presented",slide_count=10,aspect_ratio="16:9",sources=deck["sources"],
               required_native_types=["text","chart","table","diagram"],theme=theme)
    errors=validate_bundle(brief,deck)
    if errors: raise RuntimeError(errors)
    save(out/"brief.json",brief); save(out/"deck-spec.json",deck); save(out/"theme.json",t)
    ledger=check_ledger(deck,ROOT)
    if ledger.status!="passed": raise RuntimeError(ledger.issues or ledger.unknown)
    run=subprocess.run(["D:/node/node.exe",str(ROOT/"engine/build.cjs"),str(out/"deck-spec.json"),str(out/"theme.json"),str(out/"raw.pptx")],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=60)
    (out/"build.log").write_text(run.stdout+run.stderr,encoding="utf-8")
    if run.returncode: raise RuntimeError(run.stderr)
    save(out/"export-fixes.json",normalize(out/"raw.pptx",out/"deck.pptx"))
    native=inspect_native(out/"deck.pptx",deck)
    save(out/"object-map.json",native.details)
    roles={row["output_id"]:row["role"] for row in native.details.get("mapping",[])}
    inspection=inspect_deck(out/"deck.pptx",job_id=deck["job_id"],role_map=roles)
    inspection=bind_content(inspection,ledger,native)
    errors=validate(inspection.qa,"qa")
    if errors: raise RuntimeError(errors)
    save(out/"qa.json",inspection.qa); save(out/"inspection-details.json",inspection.details)
    print(json.dumps(dict(theme=theme,status=inspection.qa["status"],errors=sum(i["severity"]=="error" for i in inspection.qa["issues"]),warnings=sum(i["severity"]=="warning" for i in inspection.qa["issues"]),native=native.status,objects=len(native.details.get("mapping",[])),export_fixes=len(json.loads((out/"export-fixes.json").read_text())["edits"])),ensure_ascii=False))
    return inspection


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True,type=Path);p.add_argument("--theme",choices=list(THEMES));args=p.parse_args()
    for theme in ([args.theme] if args.theme else list(THEMES)):build(args.out.resolve()/theme,theme)
