"""Bounded, project-local WPS template adaptation; no user-document takeover."""
import json
import subprocess
from pathlib import Path
from .office_bridge import ROOT, workspace_path
from .render import powerpoint_lock, save, sha256


def validate_request(request_path, output_dir):
    request_path, out = workspace_path(request_path), workspace_path(output_dir)
    if out == ROOT / "runs" or not out.is_relative_to(ROOT / "runs") or out.exists():
        raise ValueError("Fresh output subdirectory inside runs required")
    data = json.loads(request_path.read_text(encoding="utf-8"))
    if set(data) - {"template_path", "pages", "edits"}:
        raise ValueError("Unknown WPS template request field")
    source = workspace_path(data["template_path"])
    if not source.is_file() or source.suffix.lower() not in {".pptx", ".potx"}:
        raise ValueError("Existing local PPTX/POTX required")
    pages = data["pages"]
    if not isinstance(pages, list) or not pages or len(pages) > 20 or any(type(i) is not int or i < 1 for i in pages) or pages != sorted(set(pages)):
        raise ValueError("pages must be 1–20 unique ascending positive slide numbers")
    edits = data.get("edits", [])
    if not isinstance(edits, list) or len(edits) > 100:
        raise ValueError("At most 100 text edits allowed")
    ids = set()
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"slide", "shape_id", "expected", "text"}:
            raise ValueError("Text edit requires slide, shape_id, expected, text only")
        if type(edit["slide"]) is not int or edit["slide"] not in pages or type(edit["shape_id"]) is not int or edit["shape_id"] < 1:
            raise ValueError("Text edit must target a selected slide and positive shape ID")
        if any(not isinstance(edit[k], str) or len(edit[k]) > 2000 for k in ("expected", "text")):
            raise ValueError("Text edit strings must be at most 2000 characters")
        identity = edit["slide"], edit["shape_id"]
        if identity in ids:
            raise ValueError("Duplicate text edit target")
        ids.add(identity)
    return out, {"template_path": str(source), "source_sha256": sha256(source), "pages": pages, "edits": edits}


def create_template_copy(request_path, output_dir):
    out, request = validate_request(request_path, output_dir)
    out.mkdir(parents=True, exist_ok=False)
    save(out / "request.json", request)
    with powerpoint_lock(ROOT / "runs/.powerpoint-worker-lock") as lock:
        try:
            proc = subprocess.run([str(ROOT / ".mcp-venv/Scripts/python.exe"),
                str(ROOT / "office-mcp/wps_template_worker.py"), str(out / "request.json")],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=35,
                creationflags=subprocess.CREATE_NO_WINDOW)
            save(out / "process.json", dict(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr))
            report = json.loads((out / "wps-template.json").read_text(encoding="utf-8"))
            if not report.get("cleanupCompleted"):
                save(lock / "quarantine.json", dict(reason="Owned WPS document cleanup uncertain", report=str(out)))
            if proc.returncode or report["status"] != "completed":
                raise RuntimeError(report)
            readback = subprocess.run([str(ROOT / ".mcp-venv/Scripts/python.exe"),
                str(ROOT / "office-mcp/wps_readback_worker.py"), str(out / "request.json")],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW)
            check = json.loads((out / "wps-readback.json").read_text(encoding="utf-8"))
            if not check.get("cleanupCompleted"):
                save(lock / "quarantine.json", dict(reason="WPS readback cleanup uncertain", report=str(out)))
            if readback.returncode or check["status"] != "completed":
                raise RuntimeError(check)
            report.update(readback_pending=False, edits_verified=check["edits_verified"],
                readback_report=str(out / "wps-readback.json"),
                scope="Native template copy/text edit/save/reopen/PNG export; user design approval pending")
            from .chart_preservation import verify_workbook_preservation
            preservation=verify_workbook_preservation(request['template_path'],report['deck'],request['pages'])
            save(out/'chart-preservation.json',preservation)
            report['chart_preservation']=str(out/'chart-preservation.json')
            if preservation['status']=='failed':
                report.update(status='failed',phase='chart-preservation',error='WPS copy lost embedded chart workbooks; diagnostic copy is not deliverable')
                save(out/'wps-template.json',report)
                raise RuntimeError(report['error'])
            save(out / "wps-template.json", report)
            if sha256(request["template_path"]) != request["source_sha256"]:
                raise RuntimeError("Source template changed")
            return report
        except subprocess.TimeoutExpired:
            save(lock / "quarantine.json", dict(reason="WPS template timeout; shared app retained", output=str(out)))
            raise
