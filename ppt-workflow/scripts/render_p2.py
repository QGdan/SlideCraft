"""Sequential stage sample rendering; never share Office concurrently."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import render_deck
from ppt_workflow.design import THEMES
p=argparse.ArgumentParser();p.add_argument("samples",type=Path);args=p.parse_args()
for theme in THEMES:
    d=args.samples/theme
    r=render_deck(d/"deck.pptx",d/"render",timeout=60)
    print(json.dumps(dict(theme=theme,status=r["status"],images=len(r["images"]),error=r["error"]),ensure_ascii=False),flush=True)
    if r["status"]!="passed":raise SystemExit(1)
