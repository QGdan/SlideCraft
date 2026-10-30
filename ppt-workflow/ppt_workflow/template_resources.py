"""Inventory local editable template resources without launching Office or changing inputs."""
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile
from defusedxml import ElementTree as ET
from .qa.package import NS, check_package, relationship_target

ROOT = Path(__file__).resolve().parents[1]


def inspect_template(template_path, output_dir):
    source, out = Path(template_path).resolve(), Path(output_dir).resolve()
    if not source.is_relative_to(ROOT) or not out.is_relative_to(ROOT) or out == ROOT:
        raise ValueError("Template and fresh output must stay inside ppt-workflow")
    if source.suffix.lower() not in {".potx", ".pptx"} or not source.is_file():
        raise ValueError("Existing local POTX/PPTX required; save WPS DPS as PPTX first")
    if out.exists():
        raise ValueError("Fresh output required; previous template evidence is preserved")
    package = check_package(source)
    if any(item["severity"] == "error" for item in package.issues):
        raise ValueError("Template package preflight failed: " + json.dumps(package.issues, ensure_ascii=False))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with ZipFile(source) as archive:
        names = archive.namelist()
        def xml(name):
            return ET.fromstring(archive.read(name), forbid_dtd=True)
        def relations(part):
            parent, leaf = part.rsplit("/", 1)
            relpart = parent + "/_rels/" + leaf + ".rels"
            if relpart not in names:
                return {}
            return {rel.get("Id"): relationship_target(part, rel.get("Target"))
                    for rel in xml(relpart) if rel.get("TargetMode") != "External"}
        def shapes(root):
            result = []
            for node in root.iter():
                if node.tag not in {"{" + NS["p"] + "}" + key for key in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp")}:
                    continue
                # Direct nonvisual properties avoid attributing child IDs to groups.
                props = next((child.find("p:cNvPr", NS) for child in node
                              if child.tag.rsplit("}", 1)[-1].startswith("nv")), None)
                if props is None:
                    continue
                ph = node.find("./p:nvSpPr/p:nvPr/p:ph", NS)
                result.append(dict(id=props.get("id"), name=props.get("name"),
                    kind=node.tag.rsplit("}", 1)[-1],
                    placeholder=dict(ph.attrib) if ph is not None else None,
                    text=" ".join(n.text or "" for n in node.findall("./p:txBody//a:t", NS)),
                    chart=node.find(".//{" + NS["c"] + "}chart") is not None,
                    table=node.find(".//a:tbl", NS) is not None))
            return result
        parts = {}
        for group, pattern in [("masters", r"ppt/slideMasters/slideMaster\d+\.xml"),
                               ("layouts", r"ppt/slideLayouts/slideLayout\d+\.xml"),
                               ("slides", r"ppt/slides/slide\d+\.xml")]:
            rows = []
            for name in sorted(n for n in names if re.fullmatch(pattern, n)):
                root = xml(name)
                common = root.find("p:cSld", NS)
                rows.append(dict(part=name, name=common.get("name") if common is not None else None,
                    layout_type=root.get("type"), shapes=shapes(root), related_parts=relations(name)))
            parts[group] = rows
        themes = []
        for name in sorted(n for n in names if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)):
            root = xml(name)
            themes.append(dict(part=name, name=root.get("name"),
                fonts=sorted({n.get("typeface") for n in root.iter() if n.get("typeface")}),
                colors=[dict(role=n.tag.rsplit("}", 1)[-1], color=dict(n[0].attrib))
                        for n in root.findall("./a:themeElements/a:clrScheme/*", NS) if len(n)]))
        size = xml("ppt/presentation.xml").find("p:sldSz", NS)
        report = dict(status="inventoried", source=str(source), sha256=digest,
            page_size_emu=dict(size.attrib) if size is not None else None, **parts, themes=themes,
            media_parts=[n for n in names if n.startswith("ppt/media/")],
            chart_parts=[n for n in names if re.fullmatch(r"ppt/charts/chart\d+\.xml", n)],
            scope="OOXML inventory only; not visual review, Office roundtrip or arbitrary-template compose support",
            external_resources_fetched=False, package_unknown=package.unknown)
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Template changed during inspection")
    out.mkdir(parents=True, exist_ok=False)
    target = out / "template-resources.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(status=report["status"], report=str(target), source_sha256=digest,
                counts={key:len(report[key]) for key in ("masters", "layouts", "slides", "themes", "media_parts", "chart_parts")})
