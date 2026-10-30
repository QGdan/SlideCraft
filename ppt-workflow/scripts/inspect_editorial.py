import argparse
import json
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.content import check_ledger,inspect_native,bind_content
from ppt_workflow.qa.inspect import inspect_deck,bind_render
from ppt_workflow.render import save
from ppt_workflow.contracts import validate
p=argparse.ArgumentParser();p.add_argument("sample",type=Path);p.add_argument("office",type=Path);a=p.parse_args()
spec=json.loads((a.sample/"deck-spec.json").read_text(encoding="utf-8"))
native=inspect_native(a.office/"deck.pptx",spec);ledger=check_ledger(spec,ROOT)
roles={x["output_id"]:x["role"] for x in native.details["mapping"]}
report=bind_content(inspect_deck(a.office/"deck.pptx",job_id=spec["job_id"],role_map=roles),ledger,native)
if (a.office/"render/render-manifest.json").exists():
    manifest=json.loads((a.office/"render/render-manifest.json").read_text(encoding="utf-8"))
    report=bind_render(report,manifest)
    sheet=Image.new("RGB",(1600,2250),"white")
    for i,row in enumerate(manifest["images"]):
        with Image.open(row["path"]) as im:sheet.paste(im.resize((800,450),Image.Resampling.LANCZOS),(i%2*800,i//2*450))
    sheet.save(a.office/"contact.png")
if validate(report.qa,"qa"):raise RuntimeError("Invalid QA report")
save(a.office/"qa.json",report.qa);save(a.office/"inspection-details.json",report.details);save(a.office/"object-map.json",native.details)
print(json.dumps(dict(status=report.qa["status"],native=native.status,issues=report.qa["issues"],objects=len(native.details["mapping"])),ensure_ascii=False))
