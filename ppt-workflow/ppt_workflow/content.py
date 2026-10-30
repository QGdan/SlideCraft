"""Fact ledger, declared computations and native object/data binding checks."""
from pathlib import Path
import json
import re
import math
import io
import posixpath
from zipfile import ZipFile
from defusedxml import ElementTree as ET
from pptx import Presentation
from .design import render_template,format_fact
from .qa.common import CheckResult
from .assets import check_assets

NS={"c":"http://schemas.openxmlformats.org/drawingml/2006/chart",
    "a":"http://schemas.openxmlformats.org/drawingml/2006/main",
    "r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel":"http://schemas.openxmlformats.org/package/2006/relationships",
    "s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "dgm":"http://schemas.openxmlformats.org/drawingml/2006/diagram"}


def check_ledger(deck, root=None):
    r=CheckResult(evaluated=["fact-ledger-provenance","declared-formula","cross-slide-fact-bindings","same-metric-scope-period-consistency"])
    if root is None:r.unknown.append("source-original-records-not-read")
    facts={f["id"]:f for f in deck["facts"]}; keys={}; source_map={s["id"]:s for s in deck["sources"]}
    for f in facts.values():
        for field in ["locator","period","metric"]:
            if not f.get(field): r.add("incomplete-fact-ledger",f"Fact {f['id']} lacks {field}")
        key=(f.get("metric"),f["scope"],f.get("period"))
        if key in keys and (keys[key]["value"],keys[key]["unit"])!=(f["value"],f["unit"]):
            r.add("fact-conflict",f"Conflicting values for metric/scope/period: {f['id']}")
        keys[key]=f
        src=source_map.get(f["source_id"])
        if not src: r.add("unknown-fact-source",f"Unknown source for {f['id']}"); continue
        if src["is_demo"] and not f["is_demo"]: r.add("demo-misrepresented",f"Demo source used for real fact {f['id']}")
        formula=f.get("formula")
        if formula:
            ids=formula["inputs"]
            if any(x not in facts for x in ids) or len(ids)!=2:
                r.add("formula-input",f"Invalid formula inputs for {f['id']}"); continue
            a,b=[facts[x] for x in ids]
            grouped=(deck.get('schema_version')=='0.2' and bool(a.get('comparison_group')) and
                     a.get('comparison_group')==b.get('comparison_group')==f.get('comparison_group') and
                     a['source_id']==b['source_id']==f['source_id'])
            if a["unit"]!=b["unit"] or (a["scope"]!=b["scope"] and not grouped) or a.get("period")!=b.get("period"):
                r.add("formula-scope-unit",f"Incompatible input units or scopes for {f['id']}"); continue
            if not all(isinstance(v["value"],(int,float)) for v in [a,b]):
                r.add("formula-nonnumeric",f"Non-numeric inputs for {f['id']}"); continue
            try:
                expected=a["value"]/b["value"] if formula["op"]=="divide" else a["value"]-b["value"]
                unit="倍" if formula["op"]=="divide" else a["unit"]
                if deck.get('schema_version')=='0.2' and formula['op']=='subtract' and a['unit']=='%':unit='百分点'
                if not isinstance(f["value"],(int,float)) or not math.isclose(expected,f["value"],rel_tol=1e-9) or f["unit"]!=unit:
                    r.add("formula-mismatch",f"Formula result/units do not match fact {f['id']}")
                if (f["scope"]!=a["scope"] and not grouped) or f.get("period")!=a.get("period") or f["is_demo"]!=any(facts[x]["is_demo"] for x in ids):
                    r.add("formula-provenance",f"Derived provenance mismatch for {f['id']}")
            except ZeroDivisionError: r.add("formula-zero-division",f"Zero denominator for {f['id']}")
        if root:
            if src["kind"]=="demo":
                try:
                    p=(Path(root)/src["locator"]).resolve()
                    if not p.is_relative_to(Path(root).resolve()): raise ValueError("Source escapes workspace")
                    original=json.loads(p.read_text(encoding="utf-8"))
                    for token in f["locator"].lstrip("/").split("/"): original=original[token]
                    if original!=f: r.add("source-fact-mismatch",f"Ledger differs from original source record {f['id']}")
                except Exception as exc: r.add("source-not-resolved",f"Cannot resolve {f['id']}: {exc}")
            else: r.unknown.append(f"{f['source_id']}:external-source-truth-not-reviewed")
    for page in deck["slides"]:
        if any(source_map.get(x,{}).get("is_demo") for x in page["source_refs"]):
            if not any(e["role"]=="source" and "示意" in e.get("text","") and "非实测" in e.get("text","") for e in page["elements"]):
                r.add("demo-disclosure-missing","Demo disclosure absent",slide_id=page["id"])
        for e in page["elements"]:
            kw=dict(slide_id=page["id"],element_id=e["id"])
            if e.get("text_template"):
                try:
                    refs=set(re.findall(r"\{fact:([A-Za-z0-9_-]+)\}",e["text_template"]))
                    if refs!=set(e["fact_refs"]) or e["text"]!=render_template(e["text_template"],facts):
                        r.add("text-fact-mismatch","Rendered text differs from declared facts",**kw)
                except KeyError: r.add("binding-unknown-fact","Unknown text fact",**kw)
            elif e["type"]=="text" and e["fact_refs"]:
                r.add("text-binding-missing","Fact-bearing text requires text_template",**kw)
            if e["type"]=="text" and re.search(r"\d+(?:\.\d+)?\s*(?:分钟|秒|倍)",e["text"]) and not e.get("text_template"):
                r.add("unbound-numeric-claim","Numeric duration/ratio claim requires a declared fact template",**kw)
            if e["type"]=="chart":
                refs=[]
                for s in e["chart"]["series"]:
                    ids=s.get("fact_ids",[]); refs+=ids
                    if len(ids)!=len(s["values"]): r.add("chart-binding-missing","Each chart value needs one fact ID",**kw); continue
                    for fid,value in zip(ids,s["values"]):
                        if fid not in facts or facts[fid]["value"]!=value or facts[fid]["unit"]!=e["chart"]["unit"]:
                            r.add("chart-fact-mismatch","Chart value or unit differs from ledger",**kw)
                if set(refs)!=set(e["fact_refs"]): r.add("binding-reference-mismatch","Chart bindings differ from fact_refs",**kw)
            if e["type"]=="table":
                rows=e["table"]["rows"]; ids=e["table"].get("fact_ids",[])
                refs={f for row in ids for f in row if f}
                if len(ids)!=len(rows) or any(len(a)!=len(b) for a,b in zip(ids,rows)):
                    r.add("table-binding-missing","Table cell binding dimensions mismatch",**kw); continue
                for row,rr in zip(rows,ids):
                    for value,fid in zip(row,rr):
                        if fid and (fid not in facts or str(value)!=format_fact(facts[fid])):
                            r.add("table-fact-mismatch","Table cell differs from ledger",**kw)
                if refs!=set(e["fact_refs"]): r.add("binding-reference-mismatch","Table bindings differ from fact_refs",**kw)
    assets=check_assets(deck)
    r.issues+=assets.issues;r.unknown+=assets.unknown;r.evaluated+=assets.evaluated
    return r


def workbook_range(blob, formula):
    match=re.fullmatch(r"(?:'([^']+)'|([^!]+))!\$([A-Z]+)\$(\d+)(?::\$([A-Z]+)\$(\d+))?",formula)
    if not match: raise ValueError(f"Unsupported workbook reference {formula}")
    sheet=match[1] or match[2]; c1,r1,c2,r2=match.groups()[2:]; c2=c2 or c1; r2=r2 or r1; r1,r2=int(r1),int(r2)
    if c1!=c2 or r2<r1: raise ValueError("Only ordered single-column ranges supported")
    with ZipFile(io.BytesIO(blob)) as z:
        wb=ET.fromstring(z.read("xl/workbook.xml"),forbid_dtd=True)
        rels=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"),forbid_dtd=True)
        rid=next(s.get(f"{{{NS['r']}}}id") for s in wb.findall("s:sheets/s:sheet",NS) if s.get("name")==sheet)
        target=next(s.get("Target") for s in rels if s.get("Id")==rid)
        path=posixpath.normpath(posixpath.join("xl",target)) if not target.startswith("/") else target.lstrip("/")
        strings=[]
        if "xl/sharedStrings.xml" in z.namelist():
            strings=["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml"),forbid_dtd=True)]
        cells={}
        for c in ET.fromstring(z.read(path),forbid_dtd=True).findall(".//s:c",NS):
            v=c.find("s:v",NS); kind=c.get("t")
            if kind=="s": value=strings[int(v.text)]
            elif kind=="inlineStr": value="".join(t.text or "" for t in c.findall("s:is//s:t",NS))
            elif v is not None: value=float(v.text)
            else: value=None
            cells[c.get("r")]=value
        return [cells.get(f"{c1}{row}") for row in range(r1,r2+1)]


def inspect_native(path,deck):
    r=CheckResult(evaluated=["spec-output-object-mapping","native-chart-cache-and-workbook","native-table-cells","native-diagram-parts"])
    mapping=[]; prs=Presentation(path)
    if len(prs.slides)!=len(deck["slides"]): r.add("output-slide-count","Output page count differs from spec"); return r
    with ZipFile(path) as z:
        for slide_number,(page,slide) in enumerate(zip(deck["slides"],prs.slides),1):
            names={}
            parents={}
            def visit(shapes,parent=None):
                for sh in shapes:
                    names.setdefault(sh.name,[]).append(sh);parents[sh.shape_id]=parent
                    if sh.shape_type==6:visit(sh.shapes,sh.name)
            visit(slide.shapes)
            for e in page["elements"]:
                kw=dict(slide_id=page["id"],element_id=e["id"])
                if len(names.get(e["id"],[]))!=1: r.add("object-mapping","Missing or duplicate native object name",**kw); continue
                sh=names[e["id"]][0]
                if e.get('group_id') and parents.get(sh.shape_id)!=e['group_id']:
                    r.add('native-group-mismatch','Object is outside its declared semantic group',**kw)
                if e.get('connection'):
                    c=e['connection'];nv=sh.element.find('p:nvCxnSpPr/p:cNvCxnSpPr',{'p':'http://schemas.openxmlformats.org/presentationml/2006/main'})
                    for tag,key,site in [('stCxn','from_id','from_site'),('endCxn','to_id','to_site')]:
                        bind=nv.find('a:'+tag,NS) if nv is not None else None;target=names.get(c[key],[])
                        if bind is None or len(target)!=1 or bind.get('id')!=str(target[0].shape_id) or bind.get('idx')!=str(c[site]):
                            r.add('native-connector-mismatch','Native connector endpoint differs from declared shape/site',**kw)
                mapping.append(dict(spec_id=e["id"],slide_id=page["id"],output_id=f"slide-{slide_number}/shape-{sh.shape_id}",
                                    name=sh.name,type=e["type"],role=e["role"],group_id=e.get("group_id")))
                if e["type"]=="text" and (not sh.has_text_frame or sh.text.replace("\x0b","\n")!=e["text"]): r.add("native-text-mismatch","Native text differs from spec",**kw)
                if e["type"]=="image":
                    import hashlib
                    asset=next((a for a in deck.get("assets",[]) if a["id"]==e.get("asset_id")),None)
                    if sh.shape_type!=13 or not asset or hashlib.sha256(sh.image.blob).hexdigest()!=asset["sha256"]:
                        r.add("raster-output-mismatch","Output image differs from registered raster asset",**kw)
                if e["type"]=="smartart":
                    try:
                        rels=sh.element.find(".//dgm:relIds",NS)
                        if rels is None:raise ValueError("Expected native SmartArt data relationship")
                        part=sh.part.related_part(rels.get(f"{{{NS['r']}}}dm"))
                        data=ET.fromstring(part.blob,forbid_dtd=True)
                        texts=[t.text for t in data.findall(".//a:t",NS) if t.text]
                        if texts!=e["smartart"]["nodes"]:raise ValueError(f"SmartArt text differs from spec: {texts}")
                        r.details.setdefault("smartart",[]).append(dict(element_id=e["id"],part=str(part.partname),nodes=texts,verified=True))
                    except Exception as exc:r.add("native-smartart-mismatch",str(exc),**kw)
                if e["type"]=="diagram":
                    texts=[t.text for t in sh.element.findall(".//a:t",NS) if t.text]
                    if sh.shape_type!=6 or texts!=e["diagram"]["nodes"]:r.add("native-diagram-text-mismatch","Native grouped process differs from declared nodes",**kw)
                    else:r.details.setdefault("diagrams",[]).append(dict(element_id=e["id"],nodes=texts,native_group=True,verified=True))
                if e["type"]=="table":
                    expected=[e["table"]["columns"]]+e["table"]["rows"]
                    if not sh.has_table or [[c.text for c in row.cells] for row in sh.table.rows]!=[["" if v is None else str(v) for v in row] for row in expected]:
                        r.add("native-table-mismatch","Native table differs from spec",**kw)
                if e["type"]=="chart":
                    if not sh.has_chart: r.add("native-chart-missing","Chart not native",**kw); continue
                    expected_types={'bar':{57},'column':{51},'line':{4,65}}.get(e['chart']['kind'],set())
                    part=str(sh.chart.part.partname).lstrip("/"); root=ET.fromstring(z.read(part),forbid_dtd=True)
                    type_verified=True
                    try:
                        if int(sh.chart.chart_type) not in expected_types:r.add('native-chart-type-mismatch','Chart type differs from declared kind',**kw)
                    except (KeyError,ValueError,NotImplementedError) as exc:
                        type_verified=False
                        r.unknown.append(f"native-chart-type-unrecognized:{e['id']}:{type(exc).__name__}:{exc}")
                        tag={'bar':'barChart','column':'barChart','line':'lineChart'}.get(e['chart']['kind'])
                        if tag and root.find('.//c:'+tag,NS) is None:r.add('native-chart-type-mismatch','Chart XML plot differs from declared kind',**kw)
                    try:
                        relpath=posixpath.join(posixpath.dirname(part),"_rels",posixpath.basename(part)+".rels")
                        rels=ET.fromstring(z.read(relpath),forbid_dtd=True)
                        rid=root.find("c:externalData",NS).get(f"{{{NS['r']}}}id")
                        relation=next(rel for rel in rels if rel.get("Id")==rid)
                        target=relation.get('Target')
                        if not target or relation.get('TargetMode')=='External':raise ValueError('Internal chart workbook missing; external or empty data link cannot be certified')
                        workbook=z.read(posixpath.normpath(posixpath.join(posixpath.dirname(part),target)))
                        series=root.findall(".//c:ser",NS)
                        if len(series)!=len(e["chart"]["series"]): raise ValueError("Series count differs")
                        for actual,want in zip(series,e["chart"]["series"]):
                            for parent,expected,ref,cache in [("tx",[want["name"]],"strRef","strCache"),("cat",e["chart"]["categories"],"strRef","strCache"),("val",want["values"],"numRef","numCache")]:
                                node=actual.find(f"c:{parent}/c:{ref}",NS)
                                if node is None and parent=="cat":
                                    node=actual.find("c:cat/c:multiLvlStrRef",NS)
                                    levels=node.findall("c:multiLvlStrCache/c:lvl",NS) if node is not None else []
                                    if len(levels)!=1: raise ValueError("Unsupported multi-level category cache")
                                    points=levels[0].findall("c:pt",NS)
                                elif node is not None: points=node.findall(f"c:{cache}/c:pt",NS)
                                else: raise ValueError(f"Missing supported {parent} reference")
                                if [int(p.get('idx')) for p in points]!=list(range(len(expected))): raise ValueError("Chart cache point order differs")
                                cached=[p.find("c:v",NS).text for p in points]
                                if parent=="val": cached=[float(v) for v in cached]
                                if cached!=expected or workbook_range(workbook,node.find("c:f",NS).text)!=expected:
                                    raise ValueError(f"{parent} cache/workbook differs from spec")
                        r.details.setdefault("charts",[]).append(dict(element_id=e["id"],part=part,embedded_workbook_bytes=len(workbook),verified=True,type_verified=type_verified))
                    except Exception as exc: r.add("native-chart-data-mismatch",str(exc),**kw)
                if e["type"] in {"shape","line"}:
                    geom=sh.element.find(".//a:prstGeom",NS)
                    expected=e.get('shape_kind','rect') if e['type']=='shape' else e.get('connection',{}).get('geometry','line')
                    if geom is None or geom.get("prst")!=expected:
                        r.add("native-diagram-mismatch","Native geometry differs from declared preset/connector",**kw)
    r.details["mapping"]=mapping
    return r


def bind_content(inspection,ledger,native):
    import copy
    out=copy.deepcopy(inspection)
    for stage,result in [("content",ledger),("editability",native)]:
        for i,issue in enumerate(result.issues): out.qa["issues"].append(dict(id=f"p2-{stage}-{i+1}",**issue))
        out.qa["stages"][stage]=dict(status=result.status,evidence=result.evaluated)
        if result.status!="passed": out.qa["stages"][stage]["reason"]=";".join(result.unknown) or "Error findings"
        out.qa["coverage"]["evaluated"]+=result.evaluated
        out.qa["coverage"]["unknown"]+=result.unknown
    # Static native verification is complete; interactive PowerPoint edit test stays separately unknown.
    out.qa["coverage"]["unknown"]=[x for x in out.qa["coverage"]["unknown"] if x!="source-grounded-content-review-is-P2"]
    out.qa["coverage"]["unknown"]=sorted(set(out.qa["coverage"]["unknown"]+["PowerPoint-edit-roundtrip-not-executed"]))
    out.qa["stages"]["editability"]["status"]="failed" if native.status=="failed" else "unverified"
    out.qa["stages"]["editability"]["reason"]="Native object errors" if native.status=="failed" else "Native data verified; interactive edit roundtrip not executed"
    if any(i["severity"]=="error" for i in out.qa["issues"]): out.qa["status"]="failed"
    out.details["content"]=dict(ledger=ledger.details,native=native.details)
    return out
