"""File-based orchestration. Automated unknowns are never delivery approvals."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from zipfile import ZipFile, ZIP_DEFLATED

from .contracts import validate_bundle, validate
from .content import check_ledger, inspect_native, bind_content
from .export_fix import normalize
from .qa.inspect import inspect_deck, bind_render
from .render import sha256, render_deck, verify_images
from .unified import PROFILE, check_unified_consistency

ROOT = Path(__file__).resolve().parents[1]
MAX_REVISIONS = 2
MAX_ENV_RETRIES = 1
MAX_VISUAL_API_CALLS = 3


class WorkflowError(ValueError):
    pass


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def local(path, base=ROOT):
    result = (Path(base) / path).resolve()
    if not result.is_relative_to(ROOT) or not result.is_file():
        raise WorkflowError(f"Existing project-local input required: {path}")
    return result


def fresh_run(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / "runs") or path == ROOT / "runs":
        raise WorkflowError("Job outputs must be a new subdirectory of ppt-workflow/runs")
    return path


@contextmanager
def locked(run):
    path = Path(run) / ".workflow-lock"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
    except FileExistsError as exc:
        raise WorkflowError("Job is busy; an existing lock is not removed automatically") from exc
    try:
        yield
    finally:
        path.unlink()


def file_records(paths):
    return [{"path": str(p), "sha256": sha256(p)} for p in sorted(set(map(Path, paths)), key=str)]


def engine_files():
    files = []
    for folder, pattern in [("ppt_workflow", "*.py"), ("engine", "*.cjs"), ("engine", "*.json"), ("schemas", "*.json"),
                            ("office-mcp", "*.py"), ("render", "*.ps1")]:
        files.extend((ROOT / folder).rglob(pattern))
    files.extend(ROOT / name for name in ["package-lock.json", "requirements.lock.txt", "office-mcp/requirements.lock.txt", "scripts/office_mcp_client.py"])
    files.extend((ROOT / "node_modules/pptxgenjs/dist").glob("*.js"))
    files.append(ROOT / "node_modules/pptxgenjs/package.json")
    files.append(ROOT / "skill-routing.json")
    files.extend(p for p in (ROOT / 'skills').rglob('*') if p.is_file() and p.suffix in ('.md','.json','.yaml','.py'))
    return files


def input_files(config_path, config, spec):
    base = config_path.parent
    files = [config_path] + [local(config[k], base) for k in ("brief", "spec", "template", "design_system")]
    for source in spec["sources"]:
        if source["kind"] in {"file", "demo"}:
            files.append(local(source["locator"]))
    for asset in spec.get("assets", []):
        files.append(local(asset["path"]))
    files.extend(local(p, base) for p in config.get("source_files", []))
    return files


def check_input(brief, spec):
    errors = validate_bundle(brief, spec)
    if errors:
        raise WorkflowError("Contract: " + "; ".join(errors))
    layouts = {l["key"] for l in read(PROFILE)["layouts"]}
    if not 8 <= len(spec["slides"]) <= 20 or any(s["layout"] not in layouts for s in spec["slides"]):
        raise WorkflowError("This CLI supports 8–20 pages using the approved unified-v3 layouts")
    for page in spec["slides"]:
        for element in page["elements"]:
            if element["type"] == "chart":
                chart = element["chart"]
                if spec['schema_version']=='0.1' and (chart["kind"] != "bar" or len(chart["series"]) != 1 or len(chart["categories"]) != 2):
                    raise WorkflowError("Current native chart styling supports one two-category horizontal bar series")
                if spec['schema_version']=='0.1' and any(v < 0 for series in chart['series'] for v in series['values']):
                    raise WorkflowError('Current native bar chart requires nonnegative values; signed axes are not supported')
            if spec['schema_version']=='0.1' and element["type"] == "table" and len(element["table"]["columns"]) != 3:
                raise WorkflowError("Current unified table styling supports three columns")
            if element["type"] not in {"text", "image", "line", "shape", "chart", "table", "diagram"}:
                raise WorkflowError("Unsupported unified scene type")
    ledger, consistency = check_ledger(spec, ROOT), check_unified_consistency(spec)
    if ledger.status != "passed" or consistency.status != "passed":
        raise WorkflowError("Input content/design requires review: " + json.dumps(ledger.issues + consistency.issues, ensure_ascii=False))


def plan(config_path, out):
    config_path = local(config_path)
    config = read(config_path)
    base = config_path.parent
    brief_path, spec_path = [local(config[k], base) for k in ("brief", "spec")]
    brief, spec = read(brief_path), read(spec_path)
    check_input(brief, spec)
    template, design = [local(config[k], base) for k in ("template", "design_system")]
    if template.suffix.lower() != ".potx" or sha256(design) != sha256(PROFILE):
        raise WorkflowError("Approved unified-v3 POTX and design system required")
    approval = config.get("design_approval", {})
    expected = {"spec_sha256": sha256(spec_path), "template_sha256": sha256(template), "design_sha256": sha256(design)}
    if any(approval.get(k) != v for k, v in expected.items()) or not approval.get("reviewer") or not approval.get("evidence"):
        raise WorkflowError("Hash-bound template/content approval is missing or stale")
    node = config.get("node") or shutil.which("node")
    if not node or not Path(node).is_file():
        raise WorkflowError("Node executable not found; run doctor")
    if not 1 <= config.get("timeout_seconds", 60) <= 120:
        raise WorkflowError("timeout_seconds must be between 1 and 120")
    if config.get("renderer", "powerpoint") not in {"powerpoint", "libreoffice"}:
        raise WorkflowError("Unknown renderer")
    records = file_records(input_files(config_path, config, spec) + engine_files() + [Path(node)])
    out = fresh_run(out)
    out.mkdir(parents=True, exist_ok=False)
    write(out / "inputs.json", records)
    write(out / "config.json", {**config, "node": str(Path(node).resolve()), "template": str(template), "design_system": str(design)})
    revision = out / "rev-000"
    revision.mkdir()
    write(revision / "brief.json", brief)
    write(revision / "deck-spec.json", spec)
    write(out / "state.json", {"version": 1, "job_id": spec["job_id"], "status": "planned", "revision": 0,
          "input_digest": digest(records), "visual_api_calls": 0, "environment_retries": 0,
          "created_at": datetime.now(timezone.utc).isoformat(), "history": [{"event": "plan", "revision": 0}],
          "revision_files": file_records([revision / "brief.json", revision / "deck-spec.json"]),
          "config_sha256": sha256(out / "config.json")})
    write(out / "outline.json", [{"id": s["id"], "title": s["title"], "message": s["message"], "layout": s["layout"]} for s in spec["slides"]])
    return read(out / "state.json")


def load_job(run):
    run = fresh_run(run)
    state = read(run / "state.json")
    records = read(run / "inputs.json")
    if digest(records) != state["input_digest"]:
        raise WorkflowError("Input manifest was changed; re-plan")
    try:
        mismatch = any(sha256(row["path"]) != row["sha256"] for row in records + state["revision_files"])
        mismatch |= sha256(run / "config.json") != state["config_sha256"]
        mismatch |= {str(p) for p in engine_files()} - {r["path"] for r in records} != set()
    except OSError:
        mismatch = True
    if mismatch:
        state["status"] = "needs_review"
        state["history"].append({"event": "inputs-changed", "revision": state["revision"]})
        write(run / "state.json", state)
        raise WorkflowError("Input/spec/source/theme/engine changed; prior review invalid; re-plan")
    return run, state, run / f"rev-{state['revision']:03d}"


def command(argv, directory, log, timeout):
    start = time.perf_counter()
    completed = subprocess.run(list(map(str, argv)), cwd=directory, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    write(log, {"command": list(map(str, argv)), "returncode": completed.returncode,
                "stdout": completed.stdout, "stderr": completed.stderr, "seconds": time.perf_counter() - start})
    if completed.returncode:
        raise RuntimeError(f"Worker exit {completed.returncode}; see {log.name}")


def _artifact_ok(state, revision):
    return state.get("deck_sha256") == sha256(revision / "deck.pptx")


def build(run, *, resume=False, retry_environment=False):
    with locked(run):
        run, state, revision = load_job(run)
        if state["status"] in {"built", "needs_review", "unverified", "ready", "delivered"} and (revision / "deck.pptx").exists():
            if not _artifact_ok(state, revision):
                raise WorkflowError("Built PPTX changed; rebuild in a new job")
            if resume:
                return state
            raise WorkflowError("Already built; use --resume for an unchanged job")
        if state["status"] == "failed":
            if not retry_environment or state.get("failure_kind") != "environment" or state["environment_retries"] >= MAX_ENV_RETRIES:
                raise WorkflowError("Environment retry requires explicit --retry-environment and is limited to one per job")
            state["environment_retries"] += 1
        elif state["status"] != "planned":
            raise WorkflowError(f"Cannot build from {state['status']}")
        config = read(run / "config.json")
        check_input(read(revision / "brief.json"), read(revision / "deck-spec.json"))
        attempt = revision / f"build-{state['environment_retries']:03d}"
        attempt.mkdir(exist_ok=False)
        state["status"] = "building"
        write(run / "state.json", state)
        started = time.perf_counter()
        try:
            sample = attempt / "sample"
            sample.mkdir()
            shutil.copy2(revision / "deck-spec.json", sample / "deck-spec.json")
            write(sample / "template-profile.json", {"source_template": config["template"], "template_sha256": sha256(config["template"]),
                  "design_system": config["design_system"], "design_system_sha256": sha256(config["design_system"])})
            command([config["node"], ROOT / "engine/editorial_build.cjs", sample / "deck-spec.json", sample / "raw.pptx"],
                    ROOT, attempt / "node-process.json", config.get("timeout_seconds", 60))
            write(attempt / "export-fixes.json", normalize(sample / "raw.pptx", sample / "normalized.pptx"))
            office = attempt / "office"
            command([ROOT / ".mcp-venv/Scripts/python.exe", ROOT / "scripts/office_mcp_client.py", "enhance", office, sample],
                    ROOT, attempt / "mcp-process.json", 90)
            record = read(office / "office-worker.json")
            if record.get("status") != "completed" or record.get("cleanupCompleted") is not True:
                raise RuntimeError("Missing owned Office completion evidence")
            shutil.copy2(office / "deck.pptx", revision / "deck.pptx")
            state.update(status="built", deck_sha256=sha256(revision / "deck.pptx"), build_seconds=time.perf_counter()-started,
                         build_attempt=str(attempt))
            # A worker finishing does not excuse changes to its dependencies while running.
            load_job(run)
        except Exception as exc:
            state.update(status="failed", failure_kind="environment", error=f"{type(exc).__name__}: {exc}")
            write(attempt / "failure.json", {"error": state["error"], "seconds": time.perf_counter()-started})
            write(run / "state.json", state)
            raise WorkflowError(state["error"]) from exc
        state["history"].append({"event": "build", "revision": state["revision"], "attempt": str(attempt)})
        write(run / "state.json", state)
        return state


def review_binding(state, qa_path, manifest, spec_path):
    return {"input_digest": state["input_digest"], "revision": state["revision"], "deck_sha256": state["deck_sha256"],
            "spec_sha256": sha256(spec_path), "qa_sha256": sha256(qa_path),
            "images": [{"slide": x["slide"], "sha256": x["sha256"]} for x in manifest.get("images", [])]}


def check_visual_review(review, binding, slide_count):
    if review.get("binding") != binding or review.get("status") != "passed" or not review.get("reviewer"):
        raise WorkflowError("Visual review missing, failed, or bound to a different revision")
    if review.get("method") not in {"host-image-inspection", "visual-api"}:
        raise WorkflowError("Visual review must identify the inspection method")
    pages = review.get("pages", [])
    if sorted(p.get("slide") for p in pages) != list(range(1, slide_count+1)):
        raise WorkflowError("Visual review must cover each page exactly once")
    if any(p.get("status") != "passed" or not p.get("notes") for p in pages):
        raise WorkflowError("Every page needs a passed review and concrete notes")
    if not review.get("consistency_notes") or not review.get("content_notes"):
        raise WorkflowError("Cross-page and content review notes required")


def _recompute(qa):
    qa["coverage"]["evaluated"] = list(dict.fromkeys(qa["coverage"]["evaluated"]))
    qa["coverage"]["unknown"] = list(dict.fromkeys(qa["coverage"]["unknown"]))
    if any(s["status"] == "failed" for s in qa["stages"].values()) or any(i["severity"] == "error" for i in qa["issues"]):
        qa["status"] = "failed"
    elif qa["coverage"]["unknown"] or any(s["status"] != "passed" for s in qa["stages"].values()):
        qa["status"] = "unverified"
    else:
        qa["status"] = "passed"


def qa(run, *, review_path=None, retry_environment=False):
    with locked(run):
        run, state, revision = load_job(run)
        retryable_render = (retry_environment and state["status"] == "failed" and state.get("qa_directory")
                            and read(Path(state["qa_directory"]) / "render-manifest.json").get("status") != "passed")
        if (state["status"] not in {"built", "needs_review", "unverified", "ready"} and not retryable_render) or not _artifact_ok(state, revision):
            raise WorkflowError("QA requires an unchanged built deck")
        if review_path:
            verify_evidence(state)
        renderer = read(run / "config.json").get("renderer", "powerpoint")
        existing = sorted(revision.glob("render-*/render-manifest.json"))
        if existing and read(existing[-1])["status"] == "passed":
            render_manifest = read(existing[-1])
        else:
            if existing:
                if not retry_environment or state["environment_retries"] >= MAX_ENV_RETRIES:
                    raise WorkflowError("Render retry requires --retry-environment; maximum one environment retry per job")
                state["environment_retries"] += 1
                write(run / "state.json", state)
            render_manifest = render_deck(revision / "deck.pptx", revision / f"render-{len(existing):03d}", renderer=renderer)
        spec = read(revision / "deck-spec.json")
        native = inspect_native(revision / "deck.pptx", spec)
        roles = {x["output_id"]: x["role"] for x in native.details["mapping"]}
        report = bind_content(inspect_deck(revision / "deck.pptx", job_id=spec["job_id"], revision=state["revision"], role_map=roles),
                              check_ledger(spec, ROOT), native)
        report = bind_render(report, render_manifest)
        consistency = check_unified_consistency(spec, revision / "deck.pptx")
        for index, issue in enumerate(consistency.issues):
            report.qa["issues"].append({"id": f"consistency-{index}", **issue})
        report.qa["coverage"]["evaluated"] += consistency.evaluated
        _recompute(report.qa)
        if review_path:
            previous = Path(state["qa_directory"])
            # The reviewer saw this immutable report, not a newly timestamped copy.
            report.qa = read(previous / "automated-qa.json")
            report.details = read(previous / "inspection-details.json")
        directory = revision / f"qa-{len(list(revision.glob('qa-*'))):03d}"
        directory.mkdir()
        write(directory / "automated-qa.json", report.qa)
        write(directory / "inspection-details.json", report.details)
        write(directory / "object-map.json", native.details)
        write(directory / "consistency.json", {"status": consistency.status, "issues": consistency.issues, "details": consistency.details})
        binding = review_binding(state, directory / "automated-qa.json", render_manifest, revision / "deck-spec.json")
        write(directory / "review-request.json", {"binding": binding, "status": "needs_review", "reviewer": "", "method": "host-image-inspection",
              "pages": [{"slide": i+1, "status": "needs_review", "notes": ""} for i in range(len(spec["slides"]))],
              "consistency_notes": "", "content_notes": "", "remaining_automated_unknown": report.qa["coverage"]["unknown"]})
        if review_path:
            review = read(review_path)
            check_visual_review(review, binding, len(spec["slides"]))
            if render_manifest.get("status") != "passed":
                raise WorkflowError("Cannot accept visual review without verified render images")
            if review["method"] == "visual-api":
                ticket = next((t for t in state.get("visual_tickets", []) if t["id"] == review.get("visual_ticket")), None)
                if not ticket or ticket["used"] or ticket["binding"] != binding:
                    raise WorkflowError("A fresh hash-bound visual call reservation is required")
                ticket["used"] = True
            write(directory / "visual-review.json", review)
            report.qa["stages"]["visual"] = {"status": "passed", "evidence": ["hash-bound per-page visual review", review["reviewer"]]}
            report.qa["coverage"]["unknown"] = [x for x in report.qa["coverage"]["unknown"] if x != "visual-review-not-executed"]
            report.qa["coverage"]["evaluated"].append("host-or-api-image-review")
        _recompute(report.qa)
        errors = validate(report.qa, "qa")
        if errors:
            raise WorkflowError("Invalid QA: " + "; ".join(errors))
        write(directory / "qa.json", report.qa)
        write(directory / "render-manifest.json", render_manifest)
        evidence = [p for p in directory.rglob('*') if p.is_file()] + [Path(x["path"]) for x in render_manifest.get("images", [])]
        no_warnings = not any(i["severity"] == "warning" for i in report.qa["issues"])
        state.update(status="failed" if report.qa["status"] == "failed" else "ready" if report.qa["status"] == "passed" and no_warnings
                     else "needs_review" if not review_path else "unverified",
                     qa_directory=str(directory), qa_status=report.qa["status"], qa_evidence=file_records(evidence))
        state["history"].append({"event": "qa", "revision": state["revision"], "directory": str(directory), "status": report.qa["status"]})
        write(run / "state.json", state)
        _contact_sheet(render_manifest, revision / "contact.png")
        return state


def _contact_sheet(manifest, out):
    if manifest.get("status") != "passed":
        return
    from PIL import Image, ImageOps
    rows = math.ceil(len(manifest["images"]) / 2)
    sheet = Image.new("RGB", (1600, rows*450), "white")
    for i, row in enumerate(manifest["images"]):
        with Image.open(row["path"]) as image:
            sheet.paste(ImageOps.contain(image.convert("RGB"), (800, 450)), ((i % 2)*800, (i//2)*450))
    sheet.save(out)


def revise_spec(spec, patch, qa_report, object_map):
    """Only an evidenced text-frame expansion; never change facts, fonts or brands."""
    result = deepcopy(spec)
    by_id = {e["id"]: (s, e) for s in result["slides"] for e in s["elements"]}
    issues = {x["id"]: x for x in qa_report["issues"]}
    mapping = {x["spec_id"]: x["output_id"] for x in object_map["mapping"]}
    changes = patch.get("changes", [])
    if not changes or len({x["element_id"] for x in changes}) != len(changes):
        raise WorkflowError("Nonempty, unique local changes required")
    for change in changes:
        if set(change) != {"element_id", "issue_id", "rect"}:
            raise WorkflowError("Only evidenced frame expansion is supported; content/data/brand changes require re-plan")
        eid = change["element_id"]
        if eid not in by_id or change["issue_id"] not in issues:
            raise WorkflowError("Unknown element or QA issue")
        page, element = by_id[eid]
        issue = issues[change["issue_id"]]
        if issue["element_id"] != mapping.get(eid) or issue["rule"] not in {"confirmed-text-overflow", "text-overflow-risk", "text-width-risk", "unbreakable-token-risk"}:
            raise WorkflowError("Issue does not locate this text frame or is not an overflow finding")
        if element["type"] != "text" or element["role"] in {"title", "source", "caption"}:
            raise WorkflowError("Shared header/footer/brand objects are excluded from automatic repairs")
        old, new = element["rect"], change["rect"]
        if set(new) != {"x", "y", "w", "h"} or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in new.values()):
            raise WorkflowError("Finite rectangular geometry required")
        if new["x"] != old["x"] or new["y"] != old["y"] or new["w"] < old["w"] or new["h"] < old["h"]:
            raise WorkflowError("Repair can only expand an existing frame in place")
        if new == old or new["w"]-old["w"] > .5 or new["h"]-old["h"] > .5:
            raise WorkflowError("Frame expansion must be nonzero and bounded to 0.5in per dimension")
        if new["x"]+new["w"] > 12.6 or new["y"]+new["h"] > 6.8:
            raise WorkflowError("Repair crosses the shared template regions")
        for other in page["elements"]:
            if other is element or other["type"] == "line":
                continue
            r = other["rect"]
            if min(new["x"]+new["w"], r["x"]+r["w"])-max(new["x"], r["x"]) > .01 and min(new["y"]+new["h"], r["y"]+r["h"])-max(new["y"], r["y"]) > .01:
                raise WorkflowError("Repair would intersect another object")
        element["rect"] = new
    return result


def revise(run, patch_path):
    with locked(run):
        run, state, revision = load_job(run)
        if state["revision"] >= MAX_REVISIONS:
            raise WorkflowError("Two content repair rounds exhausted; return to human review")
        if state["status"] not in {"failed", "needs_review", "unverified"} or not state.get("qa_directory"):
            raise WorkflowError("A completed QA finding is required before local repair")
        verify_evidence(state)
        if not _artifact_ok(state, revision):
            raise WorkflowError("Deck changed after QA; repair evidence no longer matches")
        directory = Path(state["qa_directory"])
        spec = revise_spec(read(revision / "deck-spec.json"), read(patch_path), read(directory / "qa.json"), read(directory / "object-map.json"))
        check_input(read(revision / "brief.json"), spec)
        new = run / f"rev-{state['revision']+1:03d}"
        new.mkdir()
        shutil.copy2(revision / "brief.json", new / "brief.json")
        write(new / "deck-spec.json", spec)
        shutil.copy2(patch_path, new / "repair.json")
        state.update(status="planned", revision=state["revision"]+1,
                     revision_files=file_records([new / "brief.json", new / "deck-spec.json", new / "repair.json"]))
        for key in ("qa_directory", "qa_status", "qa_evidence", "deck_sha256", "failure_kind", "error"):
            state.pop(key, None)
        state["history"].append({"event": "revise", "revision": state["revision"], "all_prior_reviews_invalidated": True})
        write(run / "state.json", state)
        return state


def verify_evidence(state):
    try:
        if not state.get("qa_evidence") or any(sha256(x["path"]) != x["sha256"] for x in state["qa_evidence"]):
            raise WorkflowError("QA/render/review evidence changed; review invalid")
    except OSError as exc:
        raise WorkflowError("QA evidence missing") from exc


def deliver(run, out):
    with locked(run):
        run, state, revision = load_job(run)
        if state["status"] != "ready" or state.get("qa_status") != "passed":
            raise WorkflowError("Delivery blocked: failed, needs_review and unverified are not deliverable")
        verify_evidence(state)
        if not _artifact_ok(state, revision):
            raise WorkflowError("Deck changed after review")
        qa_dir = Path(state["qa_directory"])
        report = read(qa_dir / "qa.json")
        if report["status"] != "passed" or report["coverage"]["unknown"] or any(i["severity"] in {"error", "warning"} for i in report["issues"]):
            raise WorkflowError("Delivery requires passed QA with no unresolved warnings or unknown checks")
        review = read(qa_dir / "visual-review.json")
        manifest = read(qa_dir / "render-manifest.json")
        check_visual_review(review, review_binding(state, qa_dir / "automated-qa.json", manifest, revision / "deck-spec.json"), len(read(revision / "deck-spec.json")["slides"]))
        if manifest.get("input_sha256") != state["deck_sha256"]:
            raise WorkflowError("Render belongs to another deck")
        verify_images(Path(manifest["images"][0]["path"]).parent, manifest["expected_slide_count"], manifest["width"], manifest["height"])
        out = Path(out).resolve()
        if not out.is_relative_to(ROOT / "runs") or out.exists() or out.is_relative_to(run) or run.is_relative_to(out):
            raise WorkflowError("Delivery directory must be fresh, under runs, and separate from the job")
        out.mkdir(parents=True)
        for path in [revision / "deck.pptx", revision / "deck-spec.json", revision / "brief.json", run / "inputs.json", run / "outline.json"]:
            shutil.copy2(path, out / path.name)
            if sha256(out / path.name) != sha256(path):
                raise WorkflowError("Delivery copy verification failed; partial directory is not a release")
        if sha256(out / "deck.pptx") != state["deck_sha256"]:
            raise WorkflowError("Deck changed during delivery; partial directory is not a release")
        excluded = set(map(str, engine_files())) | {read(run / "config.json")["node"]}
        source_index = []
        for record in read(run / "inputs.json"):
            path = Path(record["path"])
            if str(path) in excluded:
                continue
            target = out / "sources" / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if sha256(target) != record["sha256"]:
                raise WorkflowError("Source changed during delivery; partial directory is not a release")
            source_index.append({"original_path": str(path), "package_path": str(target.relative_to(out)), "sha256": sha256(target)})
        write(out / "source-index.json", source_index)
        shutil.copytree(qa_dir, out / "review")
        images = out / "slides"
        images.mkdir()
        for row in manifest["images"]:
            shutil.copy2(row["path"], images / f"slide-{row['slide']:03d}.png")
            if sha256(images / f"slide-{row['slide']:03d}.png") != row["sha256"]:
                raise WorkflowError("Rendered image changed during delivery; partial directory is not a release")
        for record in state["qa_evidence"]:
            original = Path(record["path"])
            if original.is_relative_to(qa_dir) and sha256(out / "review" / original.relative_to(qa_dir)) != record["sha256"]:
                raise WorkflowError("Review changed during delivery; partial directory is not a release")
        load_job(run)
        verify_evidence(state)
        records = [{"path": str(p.relative_to(out)), "sha256": sha256(p)} for p in sorted(out.rglob('*')) if p.is_file()]
        write(out / "manifest.json", {"status": "delivered", "input_digest": state["input_digest"], "revision": state["revision"], "files": records})
        with ZipFile(out / "delivery.zip", "w", ZIP_DEFLATED) as archive:
            for p in sorted(out.rglob('*')):
                if p.is_file() and p.name != "delivery.zip":
                    archive.write(p, str(p.relative_to(out)))
        state["status"] = "delivered"
        state["history"].append({"event": "deliver", "revision": state["revision"], "directory": str(out)})
        write(run / "state.json", state)
        return {"status": "delivered", "output": str(out), "zip_sha256": sha256(out / "delivery.zip")}


def reserve_visual_call(run):
    """Reserve before a host API invocation. Failed calls also consume their ticket."""
    with locked(run):
        run, state, revision = load_job(run)
        if not state.get("qa_directory") or not _artifact_ok(state, revision):
            raise WorkflowError("Run QA on an unchanged deck before reserving a visual API call")
        verify_evidence(state)
        if state["visual_api_calls"] >= MAX_VISUAL_API_CALLS:
            raise WorkflowError("Visual API budget exhausted (three calls including initial)")
        directory = Path(state["qa_directory"])
        manifest = read(directory / "render-manifest.json")
        if manifest.get("status") != "passed":
            raise WorkflowError("Verified render required before visual API call")
        binding = review_binding(state, directory / "automated-qa.json", manifest, revision / "deck-spec.json")
        state["visual_api_calls"] += 1
        ticket = {"id": f"visual-{state['visual_api_calls']}", "binding": binding, "used": False}
        state.setdefault("visual_tickets", []).append(ticket)
        write(run / "state.json", state)
        return {"ticket": ticket, "remaining": MAX_VISUAL_API_CALLS-state["visual_api_calls"],
                "instruction": "One host API invocation per reservation. Failed calls remain consumed. No API call was made by this command."}


def benchmark(runs):
    rows = []
    for path in runs:
        run, state, revision = load_job(path)
        row = {"run": str(run), "input_digest": state["input_digest"], "revision": state["revision"], "status": state["status"],
               "build_seconds": state.get("build_seconds"), "cost": None, "human_edit_seconds": None}
        if state.get("qa_directory"):
            verify_evidence(state)
            q = read(Path(state["qa_directory"]) / "qa.json")
            row.update(qa_status=q["status"], errors=sum(i["severity"] == "error" for i in q["issues"]), unknown=len(q["coverage"]["unknown"]))
            row["render_seconds"] = read(Path(state["qa_directory"]) / "render-manifest.json").get("elapsed_seconds")
        rows.append(row)
    return {"runs": rows, "note": "Measured local runs only. Missing cost/edit time is null; this is not an open-source engine comparison."}


def doctor():
    import importlib.metadata
    import sys
    dependencies = {}
    for name in ["python-pptx", "jsonschema", "pillow", "defusedxml", "fonttools"]:
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    node = shutil.which("node")
    if not node and Path("D:/node/node.exe").is_file():
        node = "D:/node/node.exe"
    return {"python": sys.version.split()[0], "dependencies": dependencies, "node": node,
            "pptxgenjs_installed": (ROOT / "node_modules/pptxgenjs/package.json").is_file(),
            "mcp_python": (ROOT / ".mcp-venv/Scripts/python.exe").is_file(),
            "office_registry": _office_registry(), "office_com": "not-tested-by-doctor",
            "figma": "host-plugin-required; no connection assumed", "image_generation": "host-tool-required; no model ID assumed",
            "powerpoint_worker_lock": (ROOT / "runs/.powerpoint-worker-lock").exists()}


def _office_registry():
    if os.name != "nt":
        return "unsupported-platform"
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID") as key:
            return winreg.QueryValueEx(key, None)[0]
    except OSError:
        return None
