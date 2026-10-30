"""Bind real engine evidence and create contact sheets from exported screenshots."""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.qa.inspect import Inspection,bind_render
from ppt_workflow.contracts import validate

parser=argparse.ArgumentParser();parser.add_argument("directory",type=Path);args=parser.parse_args()
for directory in sorted(args.directory.iterdir()):
    if not directory.is_dir() or not (directory/"render/render-manifest.json").exists():continue
    load=lambda path:json.loads(path.read_text(encoding="utf-8"))
    old=Inspection(load(directory/"qa.json"),load(directory/"inspection-details.json"))
    manifest=load(directory/"render/render-manifest.json")
    bound=bind_render(old,manifest)
    errors=validate(bound.qa,"qa")
    if errors:raise RuntimeError(errors)
    for name,value in [("qa-rendered",bound.qa),("inspection-rendered",bound.details)]:
        (directory/f"{name}.json").write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    sheet=Image.new("RGB",(1600,2250),"white")
    for i,row in enumerate(manifest["images"]):
        with Image.open(row["path"]) as im:sheet.paste(im.resize((800,450),Image.Resampling.LANCZOS),(i%2*800,i//2*450))
    sheet.save(directory/"contact.png")
    print(json.dumps(dict(theme=directory.name,status=bound.qa["status"],errors=[i for i in bound.qa["issues"] if i["severity"]=="error"],target_bounds=len(bound.details.get("target_bounds",[]))),ensure_ascii=False))
