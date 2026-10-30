import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.editorial import editorial_deck
from ppt_workflow.contracts import validate_bundle
from ppt_workflow.content import check_ledger
from ppt_workflow.export_fix import normalize
from ppt_workflow.render import save
p=argparse.ArgumentParser();p.add_argument("out",type=Path);args=p.parse_args()
out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
deck,theme=editorial_deck()
brief=dict(schema_version="0.1",job_id=deck["job_id"],topic="教学报告自动化试点",audience="教研组与信息化团队",language="zh-CN",delivery_mode="presented",slide_count=10,aspect_ratio="16:9",sources=deck["sources"],required_native_types=["text","chart","table","diagram"],theme="business")
errors=validate_bundle(brief,deck)
if errors:raise RuntimeError(errors)
ledger=check_ledger(deck,ROOT)
if ledger.status!="passed":raise RuntimeError(ledger.issues or ledger.unknown)
save(out/"deck-spec.json",deck);save(out/"brief.json",brief);save(out/"theme.json",theme)
run=subprocess.run(["D:/node/node.exe",str(ROOT/"engine/editorial_build.cjs"),str(out/"deck-spec.json"),str(out/"raw.pptx")],capture_output=True,text=True,encoding="utf-8",timeout=60,cwd=ROOT)
(out/"build.log").write_text(run.stdout+run.stderr,encoding="utf-8")
if run.returncode:raise RuntimeError(run.stderr)
save(out/"export-fixes.json",normalize(out/"raw.pptx",out/"normalized.pptx"))
print(json.dumps(dict(slides=len(deck["slides"]),registered_ai_assets=len(deck["assets"]),facts=ledger.status,output=str(out)),ensure_ascii=False))
