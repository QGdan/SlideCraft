"""P1 standalone preflight; production CLI is planned for P3."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.qa.inspect import inspect_deck
from ppt_workflow.contracts import validate

parser = argparse.ArgumentParser()
parser.add_argument("pptx",type=Path)
parser.add_argument("--out",type=Path,required=True)
parser.add_argument("--job-id",default="preflight")
parser.add_argument("--allow-outside",action="append",default=[])
args = parser.parse_args()
inspection = inspect_deck(args.pptx,job_id=args.job_id,allow_outside=args.allow_outside)
errors = validate(inspection.qa,"qa")
if errors:
    raise RuntimeError("Report violates contract: "+"; ".join(errors))
args.out.mkdir(parents=True,exist_ok=False)
for name,value in [("qa",inspection.qa),("inspection-details",inspection.details)]:
    (args.out/f"{name}.json").write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
print(json.dumps({"status":inspection.qa["status"],"issues":len(inspection.qa["issues"]),"unknown":len(inspection.qa["coverage"]["unknown"]),"output":str(args.out)},ensure_ascii=False))
raise SystemExit({"passed":0,"failed":1,"unverified":2,"needs_review":2}[inspection.qa["status"]])
