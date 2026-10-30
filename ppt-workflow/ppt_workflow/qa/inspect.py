"""Unified P1 report. No evidence means unverified, never implicit pass."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
from pptx import Presentation
from .common import CheckResult
from .package import check_package
from .geometry import check_geometry
from .typography import check_typography


@dataclass
class Inspection:
    qa: dict
    details: dict


def inspect_deck(path, *, job_id="preflight", revision=0, allow_outside=(), role_map=None):
    path = Path(path).resolve()
    package = check_package(path)
    geometry = CheckResult(unknown=["not-inspected"])
    typography = CheckResult(unknown=["not-inspected"])
    content = CheckResult(unknown=["source-grounded-content-review-is-P2"])
    editability = CheckResult(unknown=["PowerPoint-edit-roundtrip-not-executed"])
    inventory = []
    unsafe_rules = {"invalid-package","package-size-limit","unsafe-or-malformed-xml","duplicate-package-part","invalid-part-name"}
    if not any(i["rule"] in unsafe_rules for i in package.issues):
        try:
            prs = Presentation(path)
            records,geometry = check_geometry(prs,allow_outside)
            typography = check_typography(prs,records,role_map=role_map)
            for record in records:
                shape = record.shape
                inventory.append({"slide_id":record.slide_id,"element_id":record.element_id,
                                  "name":shape.name,"shape_type":str(shape.shape_type),"bbox_in":list(record.bounds),
                                  "text_geometry_supported":record.text_geometry_supported,
                                  "text":shape.text_frame.text if shape.has_text_frame else None,
                                  "has_chart":shape.has_chart,"has_table":shape.has_table})
                if shape.has_chart:
                    typography.unknown.append(f"{record.element_id}:chart-label-layout-not-measured")
                graphic = shape.element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}graphicData")
                if graphic is not None and not shape.has_chart and not shape.has_table:
                    typography.unknown.append(f"{record.element_id}:unsupported-graphic-data:{graphic.get('uri')}")
            editability.evaluated = ["native-object-inventory"]
        except Exception as exc:
            geometry.unknown.append(f"inspection-exception:{type(exc).__name__}:{exc}")
    results = {"package":package,"geometry":geometry,"typography":typography,"content":content,
               "render":CheckResult(unknown=["render-not-executed"]),
               "visual":CheckResult(unknown=["visual-review-not-executed"]),"editability":editability}
    issues = []
    stages = {}
    for kind,result in results.items():
        for index,issue in enumerate(result.issues):
            issues.append({"id":f"{kind}-{index+1}",**issue})
        stages[kind] = {"status":result.status,"evidence":[f"{kind}: {len(result.issues)} findings; {len(result.unknown)} unresolved checks"]}
        if result.status!="passed":
            stages[kind]["reason"] = "; ".join(result.unknown[:3]) if result.status=="unverified" else "At least one error finding"
    unknown = sorted({u for result in results.values() for u in result.unknown})
    failed = any(i["severity"]=="error" for i in issues)
    qa = {"schema_version":"0.1","job_id":job_id,"revision":revision,
          "created_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),
          "status":"failed" if failed else "unverified" if unknown else "passed",
          "artifact":{"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "0"*64},
          "stages":stages,"coverage":{"evaluated":sorted({v for result in results.values() for v in result.evaluated}),"unknown":unknown},"issues":issues}
    return Inspection(qa,{"inventory":inventory,"measurements":typography.details.get("measurements",[]),
                          "package":{"part_count":package.details.get("part_count"),"slide_parts":package.details.get("slide_parts",[])},
                          "checks":{k:{"unknown":r.unknown,"evaluated":r.evaluated} for k,r in results.items()}})


def bind_render(inspection, manifest):
    """Attach fresh render evidence and confirm ordinary, ungrouped text bounds."""
    import copy
    import math
    from PIL import Image
    report = copy.deepcopy(inspection)
    qa = report.qa
    if manifest.get("status")!="passed":
        status = "failed" if manifest.get("status")=="failed" else "unverified"
        qa["stages"]["render"] = {"status":status,"evidence":[manifest.get("error") or "render incomplete"],"reason":"Renderer did not verify images"}
        if status=="failed": qa["status"]="failed"
        return report
    images = manifest.get("images",[])
    try:
        if manifest.get("input_sha256")!=qa["artifact"]["sha256"] or not images:
            raise ValueError("Render input hash does not match inspected deck")
        expected=len(report.details["package"]["slide_parts"])
        if manifest.get("expected_slide_count")!=expected or len(images)!=expected or [item.get("slide") for item in images]!=list(range(1,expected+1)):
            raise ValueError("Render page count/indices do not match inspected deck")
        if hashlib.sha256(Path(qa["artifact"]["path"]).read_bytes()).hexdigest()!=qa["artifact"]["sha256"]:
            raise ValueError("Inspected deck changed before render binding")
        for item in images:
            file=Path(item["path"])
            if hashlib.sha256(file.read_bytes()).hexdigest()!=item["sha256"]:
                raise ValueError("Rendered image changed before binding")
            with Image.open(file) as image:
                image.load()
                if list(image.size)!=item["size_px"] or item["size_px"]!=[manifest.get("width"),manifest.get("height")]:raise ValueError("Image dimensions changed")
    except Exception as exc:
        qa["stages"]["render"]={"status":"failed","evidence":[str(exc)],"reason":"Render evidence binding failed"}
        qa["status"]="failed"
        return report
    qa["stages"]["render"]={"status":"passed","evidence":[f"input sha256:{manifest['input_sha256']}",f"verified images:{len(images)}"]}
    qa["coverage"]["unknown"]=[u for u in qa["coverage"]["unknown"] if u!="render-not-executed"]
    qa["coverage"]["evaluated"].append("render-images-hash-bound-to-input")
    inventory={item["element_id"]:item for item in report.details["inventory"]}
    measurements={item["element_id"]:item for item in report.details["measurements"]}
    confirmations=[]
    for row in manifest.get("worker",{}).get("textBounds",[]):
        eid=row.get("elementId"); record=inventory.get(eid)
        measure=measurements.get(eid)
        if not record or not measure or eid.count("/")!=1 or not record["text_geometry_supported"]:
            continue
        if any("rotated-vertical" in u or "wordart" in u for u in measure["unknown"]):
            continue
        values=row.get("rawBoundPt",[])+row.get("rawFramePt",[])
        if len(values)!=8 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
            continue
        bx,by,bw,bh,fx,fy,fw,fh=[v/72 for v in values]
        over=max(fx-bx,fy-by,bx+bw-fx-fw,by+bh-fy-fh)
        confirmations.append({"element_id":eid,"bound_in":[bx,by,bw,bh],"frame_in":[fx,fy,fw,fh],"excess_in":over})
        if over>0.08:
            qa["issues"].append({"id":f"target-bounds-{len(confirmations)}","rule":"confirmed-text-overflow","severity":"error","message":"PowerPoint computed text bounds extend beyond the declared frame","slide_id":record["slide_id"],"element_id":eid,"bbox_in":[bx,by,bw,bh],"evidence":[f"PowerPoint bounds exceed frame by {over:.3f}in"],"details":{"excess_in":round(over,4)}})
            qa["stages"]["typography"]["status"]="failed"
            qa["stages"]["typography"]["reason"]="Target-engine text bounds confirmed overflow"
            qa["status"]="failed"
    report.details["target_bounds"] = confirmations
    if confirmations:
        qa["coverage"]["evaluated"].append("target-bounds-ordinary-ungrouped-text")
    return report
