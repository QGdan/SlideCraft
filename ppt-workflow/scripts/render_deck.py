import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import render_deck
parser=argparse.ArgumentParser()
parser.add_argument("pptx",type=Path)
parser.add_argument("--out",required=True,type=Path)
parser.add_argument("--renderer",choices=["powerpoint","libreoffice"],default="powerpoint")
parser.add_argument("--timeout",type=float,default=60)
args=parser.parse_args()
report=render_deck(args.pptx,args.out,renderer=args.renderer,timeout=args.timeout)
print(json.dumps({"status":report["status"],"images":len(report["images"]),"error":report["error"]},ensure_ascii=False))
raise SystemExit(0 if report["status"]=="passed" else 2)
