"""Edit only an Untitled template copy; close owned document handles, never WPS."""
import gc
import json
from pathlib import Path
import sys
import shutil
import traceback
import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ppt_workflow.render import save, sha256

request_path = Path(sys.argv[1])
out = request_path.parent
q = json.loads(request_path.read_text(encoding="utf-8"))
result = dict(status="failed", changes=[], application_quit_called=False, cleanupCompleted=False)
owned = []
app = None
pythoncom.CoInitialize()


def find_shape(shapes, shape_id):
    for i in range(1, shapes.Count + 1):
        shape = shapes.Item(i)
        if shape.Id == shape_id:
            return shape
        if shape.Type == 6:
            nested = find_shape(shape.GroupItems, shape_id)
            if nested is not None:
                return nested
    return None


try:
    # The user may still have the original template open in the WPS UI.
    # A physical snapshot avoids WPS's modal "file locked" prompt.
    snapshot = out / ("template-input" + Path(q["template_path"]).suffix)
    shutil.copyfile(q["template_path"], snapshot)
    if sha256(snapshot) != q["source_sha256"]:
        raise RuntimeError("Template changed before snapshot")
    result["phase"] = "activate"
    try:
        app = win32com.client.GetActiveObject("KWPP.Application")
        result["activation"] = "existing-active-object"
    except pythoncom.com_error:
        app = win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}",
            clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)
        result["activation"] = "32-bit-local-server"
    result["phase"] = "open-snapshot"
    pres = app.Presentations.Open(str(snapshot), False, True, False)
    owned.append(pres)
    if max(q["pages"]) > pres.Slides.Count:
        raise ValueError("Selected slide does not exist")
    # Validate every expected value before changing the scratch copy.
    for edit in q["edits"]:
        shape = find_shape(pres.Slides.Item(edit["slide"]).Shapes, edit["shape_id"])
        if shape is None or not shape.HasTextFrame or shape.TextFrame.TextRange.Text.replace("\r", "\n") != edit["expected"]:
            raise ValueError(f"Text precondition failed: slide {edit['slide']} shape {edit['shape_id']}")
    for edit in q["edits"]:
        shape = find_shape(pres.Slides.Item(edit["slide"]).Shapes, edit["shape_id"])
        shape.TextFrame.TextRange.Text = edit["text"]
        result["changes"].append(edit)
    for index in range(pres.Slides.Count, 0, -1):
        if index not in q["pages"]:
            pres.Slides.Item(index).Delete()
    output = out / "template-adapted.pptx"
    result["phase"] = "save-and-export"
    pres.SaveAs(str(output), 24)
    images = out / "slides"
    images.mkdir()
    for index in range(1, pres.Slides.Count + 1):
        pres.Slides.Item(index).Export(str(images / f"slide-{index}.png"), "PNG", 1600, 900)
    slide_count = int(pres.Slides.Count)
    layout_count = int(pres.SlideMaster.CustomLayouts.Count)
    pres.Close()
    owned.remove(pres)
    if sha256(q["template_path"]) != q["source_sha256"]:
        raise RuntimeError("Original template changed")
    result.update(status="completed", deck=str(output), output_sha256=sha256(output),
        source_sha256=q["source_sha256"], source_pages=q["pages"],
        slide_count=slide_count, edits_verified=0, readback_pending=True,
        layout_count=layout_count,
        scope="Native template copy/text edit/save/PNG export; fresh-process readback required")
except Exception as exc:
    result["error"] = f"{type(exc).__name__}: {exc}"
    result["traceback"] = traceback.format_exc()
finally:
    for presentation in reversed(owned):
        try:
            presentation.Close()
        except Exception as exc:
            result["cleanupError"] = str(exc)
    owned.clear()
    app = None
    gc.collect()
    pythoncom.CoUninitialize()
    result["cleanupCompleted"] = "cleanupError" not in result
    save(out / "wps-template.json", result)
raise SystemExit(0 if result["status"] == "completed" and result["cleanupCompleted"] else 1)
