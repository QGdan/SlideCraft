"""Schema and semantic contracts; validation is not visual QA."""
from __future__ import annotations

import json
import math
import hashlib
import re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"


def validate(document: dict, kind: str) -> list[str]:
    if kind not in {"brief", "deck", "qa", "content-plan", "quality-review"}:
        raise ValueError(f"Unknown contract kind: {kind}")
    schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}"
              for e in sorted(validator.iter_errors(document), key=lambda e: str(list(e.absolute_path)))]
    if errors:
        return errors

    def finite(value, path="$"):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path}: non-finite numeric value")
        elif isinstance(value, dict):
            for key, item in value.items():
                finite(item, f"{path}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                finite(item, f"{path}/{index}")

    finite(document)

    def unique(items, field, label):
        identifiers = [item[field] for item in items]
        if len(set(identifiers)) != len(identifiers):
            errors.append(f"{label}: duplicate {field}")

    if kind in {"brief", "deck"}:
        unique(document["sources"], "id", "sources")
        for source in document["sources"]:
            if source["kind"] == "demo" and not source["is_demo"]:
                errors.append(f"source/{source['id']}: demo source must be marked is_demo")
    if kind == "deck":
        if document['schema_version']=='0.1' and document.get('blueprint_ref'):
            errors.append('Template blueprints require schema_version 0.2')
        if document.get('blueprint_ref'):
            ref=document['blueprint_ref'];name=ref['id']
            if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',name):errors.append('Invalid blueprint ID')
            else:
                path=SCHEMAS.parent/'templates'/name/'blueprint.json'
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:
                    errors.append('Blueprint reference is missing or stale')
                elif ref['variant'] not in json.loads(path.read_text(encoding='utf-8'))['variants']:
                    errors.append('Unknown blueprint variant')
        source_map = {s["id"]: s for s in document["sources"]}
        unique(document["facts"], "id", "facts")
        fact_map = {f["id"]: f for f in document["facts"]}
        for fact in document["facts"]:
            if document['schema_version']=='0.1' and 'comparison_group' in fact:
                errors.append(f"fact/{fact['id']}: comparison_group requires schema_version 0.2")
            if fact["source_id"] not in source_map:
                errors.append(f"fact/{fact['id']}: unknown source_id")
            elif source_map[fact["source_id"]]["is_demo"] and not fact["is_demo"]:
                errors.append(f"fact/{fact['id']}: demo source cannot support a real-world fact")
        unique(document["slides"], "id", "slides")
        elements = [e for s in document["slides"] for e in s["elements"]]
        unique(elements, "id", "elements")
        for slide in document["slides"]:
            page_elements={e['id']:e for e in slide['elements']}
            groups={e['group_id'] for e in slide['elements'] if e.get('group_id')}
            if groups & {e['id'] for e in elements}:errors.append(f"slide/{slide['id']}: group ID collides with an element ID")
            if slide['layout'] in {'scene_cover','evidence_focus','comparison_focus','photo_process','photo_process_side'} and not document.get('blueprint_ref'):
                errors.append('Scene layouts require an explicit blueprint_ref')
            for ref in slide["source_refs"]:
                if ref not in source_map:
                    errors.append(f"slide/{slide['id']}: unknown source {ref}")
            for element in slide["elements"]:
                if 'shape_kind' in element and (element['type']!='shape' or document['schema_version']!='0.2'):
                    errors.append('Native shape_kind belongs to 0.2 shape elements only')
                connection=element.get('connection')
                if connection:
                    if element['type']!='line' or document['schema_version']!='0.2':errors.append('Connection bindings belong to 0.2 native lines only')
                    endpoints=[page_elements.get(connection[k]) for k in ('from_id','to_id')]
                    if connection['from_id']==connection['to_id'] or any(e is None or e['type']!='shape' for e in endpoints):
                        errors.append(f"element/{element['id']}: connection endpoints must be different native shapes on this slide")
                    elif any(e.get('group_id')!=element.get('group_id') for e in endpoints):
                        errors.append(f"element/{element['id']}: connection and endpoints must share the same semantic group")
                if any(k in element for k in ('image_fit','image_focus')) and element['type']!='image':
                    errors.append('Image fitting fields belong to image elements only')
                if 'image_focus' in element and not element.get('image_fit'):
                    errors.append('Image focus requires explicit image_fit')
                if document['schema_version']=='0.1' and any(k in element for k in ('image_fit','image_focus')):
                    errors.append('Explicit image fitting requires schema_version 0.2')
                for ref in element["fact_refs"]:
                    if ref not in fact_map:
                        errors.append(f"element/{element['id']}: unknown fact {ref}")
                    elif fact_map[ref]["source_id"] not in slide["source_refs"]:
                        errors.append(f"element/{element['id']}: fact source not cited by slide")
                if element["type"] == "chart":
                    chart = element["chart"]
                    from .charts import validate_chart
                    errors.extend(f"element/{element['id']}: {message}" for message in validate_chart(chart, document['schema_version']))
                    for series in chart["series"]:
                        if len(series["values"]) != len(chart["categories"]):
                            errors.append(f"element/{element['id']}: chart categories/values length mismatch")
                if element["type"] == "table":
                    table = element["table"]
                    if any(len(row) != len(table["columns"]) for row in table["rows"]):
                        errors.append(f"element/{element['id']}: table column count mismatch")
    if kind == "qa":
        unique(document["issues"], "id", "issues")
        has_failure = any(s["status"] == "failed" for s in document["stages"].values())
        has_error = any(i["severity"] == "error" for i in document["issues"])
        if (has_failure or has_error) and document["status"] != "failed":
            errors.append("status: failed stages or error issues require failed overall status")
    return errors


def validate_bundle(brief: dict, deck: dict) -> list[str]:
    """Check cross-document requirements before a later build command."""
    errors = validate(brief, "brief") + validate(deck, "deck")
    if errors:
        return errors
    if brief["job_id"] != deck["job_id"]:
        errors.append("bundle: job_id mismatch")
    if brief["slide_count"] != len(deck["slides"]):
        errors.append("bundle: requested slide count does not match deck")
    if abs(deck["canvas"]["width"] / deck["canvas"]["height"] - 16 / 9) > 0.002:
        errors.append("bundle: canvas is not 16:9")
    if "theme" in brief and brief["theme"] != deck["theme"]:
        errors.append("bundle: theme mismatch")
    brief_sources = {s["id"]: s for s in brief["sources"]}
    for source in deck["sources"]:
        if source["id"] not in brief_sources or source != brief_sources[source["id"]]:
            errors.append(f"bundle: source {source['id']} differs from brief")
    required = set(brief["required_native_types"])
    found = set()
    for slide in deck["slides"]:
        for element in slide["elements"]:
            if element["editability_requirement"] == "native":
                found.add(element["type"])
                if element["role"] == "diagram":
                    found.add("diagram")
            elif element["type"] in required:
                errors.append(f"bundle: required {element['type']} element {element['id']} is not native")
    if required - found:
        errors.append(f"bundle: missing required native types {sorted(required - found)}")
    return errors
