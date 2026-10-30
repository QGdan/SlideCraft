"""Whitelisted MCP/Office operations with workspace boundaries and owned workers."""
import json
import os
import subprocess
from pathlib import Path
from .render import powerpoint_lock,save,sha256

ROOT=Path(__file__).resolve().parents[1]


def workspace_path(path):
    resolved=Path(path).resolve()
    if not resolved.is_relative_to(ROOT):raise ValueError("Office bridge path must stay inside ppt-workflow")
    return resolved


def native_operation(operation,out,*,sample=None,template=None):
    if operation not in {"catalog","enhance","instantiate","unified-template"}:raise ValueError("Unsupported Office operation")
    out=workspace_path(out)
    request=dict(operation=operation)
    worker="native_worker.py"
    if operation=="unified-template":
        worker="unified_worker.py"
        request.update(design_system=str(ROOT/"templates/unified-v3/design-system.json"),template=str(out/"Unified-Ivory.potx"),preview=str(out/"template-preview.pptx"))
    if operation=="enhance":
        sample=workspace_path(sample)
        request.update(input=str(sample/"normalized.pptx"),spec=str(sample/"deck-spec.json"),output=str(out/"deck.pptx"),template=str(out/"Editorial-Teal.potx"))
        if not Path(request["input"]).is_file() or not Path(request["spec"]).is_file():raise ValueError("Complete sample files required")
        input_hash=sha256(request["input"])
        binding=sample/"template-profile.json"
        if binding.exists():
            data=json.loads(binding.read_text(encoding="utf-8"));source=workspace_path(data["source_template"]);design=workspace_path(data["design_system"])
            if sha256(source)!=data["template_sha256"] or sha256(design)!=data["design_system_sha256"]:raise ValueError("Frozen template/profile changed")
            request.update(template_source=str(source),design_system=str(design),template=str(out/"Unified-Ivory.potx"));worker="unified_worker.py"
    elif operation=="instantiate":
        template=workspace_path(template)
        if template.suffix.lower()!=".potx" or not template.is_file():raise ValueError("Registered local POTX required")
        request.update(input=str(template),output=str(out/"from-template.pptx"));input_hash=sha256(template)
    out.mkdir(parents=True,exist_ok=False)
    save(out/"request.json",request)
    report_file=out/"office-worker.json"
    with powerpoint_lock(ROOT/"runs/.powerpoint-worker-lock") as lock:
        try:
            proc=subprocess.run([str(ROOT/".mcp-venv/Scripts/python.exe"),str(ROOT/"office-mcp"/worker),str(out/"request.json"),str(report_file)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            record=json.loads(report_file.read_text(encoding="utf-8"))
            save(out/"process.json",dict(returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr))
            if not record.get("cleanupCompleted"):
                save(lock/"quarantine.json",dict(reason="Office cleanup uncertain",report=str(report_file)))
            if proc.returncode or record["status"]!="completed" or not record.get("cleanupCompleted"):raise RuntimeError(record)
            if operation in {"enhance","instantiate"}:
                if sha256(request["input"])!=input_hash:raise RuntimeError("Original input changed during Office editing")
                record.update(input_sha256=input_hash,output_sha256=sha256(request["output"]))
                if operation=="enhance":record["template_sha256"]=sha256(request["template"])
                save(report_file,record)
            return record
        except Exception:
            if not report_file.exists():save(lock/"quarantine.json",dict(reason="Office timeout/missing cleanup evidence",report=str(out)))
            raise
