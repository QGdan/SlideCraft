"""Fresh-process native readback of a project-owned WPS output, never quits WPS."""
import gc
import json
from pathlib import Path
import sys
import traceback
import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.render import save

qpath = Path(sys.argv[1]).resolve()
if not qpath.is_relative_to(ROOT / "runs"):
    raise ValueError("Project-owned request required")
q = json.loads(qpath.read_text(encoding="utf-8"))
target = qpath.parent / "template-adapted.pptx"
report = dict(status="failed", cleanupCompleted=False, application_quit_called=False)
app = pres = None
pythoncom.CoInitialize()


def find(shapes, sid):
    for i in range(1, shapes.Count + 1):
        shape = shapes.Item(i)
        if shape.Id == sid:
            return shape
        if shape.Type == 6:
            nested = find(shape.GroupItems, sid)
            if nested is not None:
                return nested
    return None


try:
    try:
        app = win32com.client.GetActiveObject("KWPP.Application")
        report["activation"] = "existing-active-object"
    except pythoncom.com_error:
        app = win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}", clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)
        report["activation"] = "32-bit-local-server"
    report["initial_count"] = int(app.Presentations.Count)
    pres = app.Presentations.Open(str(target), True, False, False)
    report["slide_count"] = int(pres.Slides.Count)
    for edit in q["edits"]:
        shape = find(pres.Slides.Item(q["pages"].index(edit["slide"]) + 1).Shapes, edit["shape_id"])
        if shape is None or shape.TextFrame.TextRange.Text.replace("\r", "\n") != edit["text"]:
            raise RuntimeError("Native saved-text readback failed")
    report.update(status="completed", edits_verified=len(q["edits"]))
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
finally:
    if pres is not None:
        try:
            pres.Close()
        except Exception as exc:
            report["cleanupError"] = str(exc)
    pres = app = None
    gc.collect()
    pythoncom.CoUninitialize()
    report["cleanupCompleted"] = "cleanupError" not in report
    save(qpath.parent / "wps-readback.json", report)
    print(json.dumps(report, ensure_ascii=True))
raise SystemExit(0 if report["status"] == "completed" and report["cleanupCompleted"] else 1)
