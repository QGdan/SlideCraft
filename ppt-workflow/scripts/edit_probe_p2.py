"""Bounded, owned COM editing of a disposable sample copy, with reopen verification."""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from pptx import Presentation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import powerpoint_lock,save,sha256
from ppt_workflow.content import inspect_native
from ppt_workflow.qa.package import check_package

p=argparse.ArgumentParser();p.add_argument("sample",type=Path);p.add_argument("--out",required=True,type=Path);args=p.parse_args()
sample=args.sample.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
spec=json.loads((sample/"deck-spec.json").read_text(encoding="utf-8"));before=sha256(sample/"deck.pptx")
chart=next(e for s in spec["slides"] for e in s["elements"] if e["type"]=="chart")
table=next(e for s in spec["slides"] for e in s["elements"] if e["type"]=="table")
title=next(e for e in spec["slides"][0]["elements"] if e["role"]=="title")
req=dict(input=str(sample/"deck.pptx"),output=str(out/"edited-copy.pptx"),operations=[
    dict(slide=5,name=chart["id"],kind="chart-resize",delta_pt=18),
    dict(slide=8,name=table["id"],kind="table-cell",row=2,col=1,text="人工汇总（复核）"),
    dict(slide=1,name=title["id"],kind="text",text=title["text"]+"（复核）")])
save(out/"request.json",req)
worker_file=out/"worker.json";record=dict(status="unverified",input_sha256=before,scope="Chart resize; table-cell and text edits; save and reopen. Chart values not modified.")
with powerpoint_lock(ROOT/"runs/.powerpoint-worker-lock") as lock:
    try:
        run=subprocess.run([shutil.which("powershell"),"-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"render/edit_probe.ps1"),"-Request",str(out/"request.json"),"-Report",str(worker_file)],capture_output=True,text=True,encoding="utf-8",timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        record["exit_code"]=run.returncode;record["stdout"]=run.stdout;record["stderr"]=run.stderr
        worker=json.loads(worker_file.read_text(encoding="utf-8-sig"));record["worker"]=worker
        if not worker.get("cleanupCompleted"):save(lock/"quarantine.json",dict(reason="edit probe cleanup uncertain",report=str(out)))
        if run.returncode or not worker.get("cleanupCompleted") or worker.get("reopenedSlideCount")!=10:raise RuntimeError(worker)
        expected=copy.deepcopy(spec)
        expected["slides"][0]["elements"][next(i for i,e in enumerate(expected["slides"][0]["elements"]) if e["id"]==title["id"])]["text"]=req["operations"][2]["text"]
        next(e for s in expected["slides"] for e in s["elements"] if e["id"]==table["id"])["table"]["rows"][0][0]=req["operations"][1]["text"]
        native=inspect_native(out/"edited-copy.pptx",expected)
        actual=next(sh for sh in Presentation(out/"edited-copy.pptx").slides[4].shapes if sh.name==chart["id"])
        width=float(actual.width)/914400
        if abs(width-(chart["rect"]["w"]-.25))>.002:raise ValueError("Saved chart width did not retain edit")
        package=check_package(out/"edited-copy.pptx")
        if native.status!="passed" or package.issues:raise ValueError(dict(native=native.issues,package=package.issues))
        if sha256(sample/"deck.pptx")!=before:raise ValueError("Original changed during editing")
        record.update(status="passed",output_sha256=sha256(out/"edited-copy.pptx"),native=native.details,package_issues=package.issues,chart_width_in=width,original_unchanged=True)
    except Exception as exc:
        record.update(status="failed",error=str(exc))
        if not worker_file.exists():save(lock/"quarantine.json",dict(reason="edit probe timeout or missing cleanup evidence",report=str(out)))
save(out/"edit-probe.json",record)
print(json.dumps(dict(status=record["status"],error=record.get("error")),ensure_ascii=False))
raise SystemExit(0 if record["status"]=="passed" else 1)
