"""OPC and selected OOXML references; not a full schema validator."""
from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath
import posixpath
from urllib.parse import unquote
import zipfile
from defusedxml import ElementTree as ET
from .common import CheckResult

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def source_for_rels(name):
    if name == "_rels/.rels":
        return ""
    parent, leaf = name.rsplit("/_rels/", 1)
    return f"{parent}/{leaf[:-5]}"


def relationship_target(source, target):
    target = unquote(target.split("#", 1)[0])
    if not target:
        return source
    if "\\" in target or ":" in target:
        raise ValueError("Internal relationship has an invalid URI")
    resolved = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join(posixpath.dirname(source), target))
    if resolved == ".." or resolved.startswith("../"):
        raise ValueError("Relationship escapes the package")
    return resolved


def check_chart(root, part, result):
    axis_tags = {f"{{{NS['c']}}}{t}" for t in ["valAx", "catAx", "dateAx", "serAx"]}
    declarations = []
    for node in root.iter():
        if node.tag in axis_tags:
            ax = node.find("c:axId", NS)
            if ax is None or ax.get("val") is None:
                result.add("chart-axis-missing-id", f"{part}: axis declaration lacks axId")
            else:
                declarations.append(ax.get("val"))
    declared = set(declarations)
    if len(declared) != len(declarations):
        result.add("duplicate-chart-axis", f"{part}: duplicate axis declarations")
    for parent in root.iter():
        for child in parent:
            if child.tag == f"{{{NS['c']}}}axId" and parent.tag not in axis_tags:
                if child.get("val") not in declared:
                    result.add("undeclared-chart-axis", f"{part}: referenced axis {child.get('val')} is not declared")
            if child.tag == f"{{{NS['c']}}}crossAx" and child.get("val") not in declared:
                result.add("undeclared-cross-axis", f"{part}: cross-axis {child.get('val')} is not declared")


def check_package(path, max_bytes=256 * 1024 * 1024):
    result = CheckResult(evaluated=["zip-integrity", "safe-xml", "content-types", "internal-relationships", "chart-axis-references", "slide-order"],
                         unknown=["full-OOXML-schema-validation-not-run"])
    parsed = {}
    relations = {}
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [i for i in archive.infolist() if not i.is_dir()]
            names = {i.filename for i in entries}
            for name, count in Counter(i.filename for i in entries).items():
                if count > 1:
                    result.add("duplicate-package-part", f"Duplicate ZIP entry: {name}")
            if sum(i.file_size for i in entries) > max_bytes:
                result.add("package-size-limit", "Uncompressed package exceeds configured size limit")
                return result
            for info in entries:
                if info.filename.startswith("/") or ".." in PurePosixPath(info.filename).parts or "\\" in info.filename:
                    result.add("invalid-part-name", f"Invalid ZIP part: {info.filename}")
            for required in ["[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"]:
                if required not in names:
                    result.add("missing-package-part", f"Required part missing: {required}")
            for name in sorted(names):
                if name.endswith((".xml", ".rels")):
                    try:
                        parsed[name] = ET.fromstring(archive.read(name), forbid_dtd=True)
                    except Exception as exc:
                        result.add("unsafe-or-malformed-xml", f"{name}: {type(exc).__name__}: {exc}")
            # Reading every entry tests CRC without extracting anything.
            for info in entries:
                if not info.filename.endswith((".xml", ".rels")):
                    archive.read(info.filename)
            ct = parsed.get("[Content_Types].xml")
            if ct is not None:
                defaults = {n.get("Extension", "").lower() for n in ct if n.tag == f"{{{CT_NS}}}Default" and n.get("ContentType")}
                overrides = {unquote(n.get("PartName", "")).lstrip("/") for n in ct if n.tag == f"{{{CT_NS}}}Override" and n.get("ContentType")}
                for name in names - {"[Content_Types].xml"}:
                    if name not in overrides and name.rsplit(".", 1)[-1].lower() not in defaults:
                        result.add("missing-content-type", f"No content type declared for {name}")
                for name in overrides - names:
                    result.add("dangling-content-type", f"Content-type override has no part: {name}")
            for name, root in parsed.items():
                if not name.endswith(".rels"):
                    continue
                try:
                    source = source_for_rels(name)
                except ValueError:
                    result.add("invalid-relationship-part", f"Invalid relationship part location: {name}")
                    continue
                if source and source not in names:
                    result.add("orphan-relationship-part", f"{name}: source {source} missing")
                table = {}
                for rel in root:
                    rid, target = rel.get("Id"), rel.get("Target")
                    if not rid or target is None or not rel.get("Type"):
                        result.add("invalid-relationship", f"{name}: relationship lacks Id, Type or Target")
                        continue
                    if rid in table:
                        result.add("duplicate-relationship-id", f"{name}: duplicate {rid}")
                    if rel.get("TargetMode") == "External":
                        table[rid] = {"target": target, "external": True, "type": rel.get("Type")}
                        result.unknown.append(f"external-resource-not-fetched:{source}:{rid}")
                        continue
                    try:
                        resolved = relationship_target(source, target)
                    except ValueError as exc:
                        result.add("invalid-relationship-target", f"{name}: {target}: {exc}")
                        continue
                    table[rid] = {"target": resolved, "external": False, "type": rel.get("Type")}
                    if resolved not in names:
                        result.add("broken-relationship-target", f"{name}: {rid} points to missing {resolved}")
                relations[source] = table
            for name, root in parsed.items():
                if name.endswith(".rels"):
                    continue
                table = relations.get(name, {})
                for node in root.iter():
                    for attr, rid in node.attrib.items():
                        if attr in {f"{{{NS['r']}}}{t}" for t in ["id", "embed", "link"]} and rid not in table:
                            result.add("undeclared-relationship-id", f"{name}: XML references undeclared {rid}")
                if name.startswith("ppt/charts/") and name.endswith(".xml"):
                    check_chart(root, name, result)
            presentation = parsed.get("ppt/presentation.xml")
            slide_parts = []
            if presentation is not None:
                table = relations.get("ppt/presentation.xml", {})
                for sld in presentation.findall("p:sldIdLst/p:sldId", NS):
                    rel = table.get(sld.get(f"{{{NS['r']}}}id"))
                    if rel and not rel["external"]:
                        slide_parts.append(rel["target"])
                if not slide_parts:
                    result.add("empty-presentation", "Presentation contains no reachable slides")
                if len(set(slide_parts))!=len(slide_parts):
                    result.add("duplicate-slide-reference", "Presentation order references a slide part more than once")
            result.details.update(slide_parts=slide_parts, part_count=len(names), xml_parts=parsed, relations=relations)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        result.add("invalid-package", f"Cannot read package: {type(exc).__name__}: {exc}")
    return result
