"""P0 evidence: snapshot originals, rebuild a copy, record legacy checks."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

WORKFLOW = Path(__file__).resolve().parents[1]
ROOT = WORKFLOW.parent
REVIEW = ROOT / "06-实施与阶段审核" / "P0"
REVIEW.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-id must contain letters, digits, hyphens or underscores")
    run_dir = WORKFLOW / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshot = REVIEW / "snapshot"
    snapshot.mkdir(exist_ok=True)
    original_files = [ROOT / "README.md"]
    for directory in ["01-研究报告", "02-工具链", "03-示例与验收", "04-校准证据", "skill", "05-开源项目深度研究"]:
        original_files.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    records = []
    for source in sorted(original_files):
        rel = source.relative_to(ROOT)
        records.append({"path": rel.as_posix(), "size": source.stat().st_size, "sha256": sha(source)})
        destination = snapshot / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and sha(destination) != sha(source):
            raise RuntimeError(f"Existing frozen snapshot differs: {rel}")
        if not destination.exists():
            shutil.copy2(source, destination)
    manifest = {"created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "root": str(ROOT), "snapshot": str(snapshot), "originals": records}
    write(REVIEW / "baseline-manifest.json", manifest)

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    commands = []

    def run(tag, command, timeout=90):
        started = time.perf_counter()
        try:
            result = subprocess.run(command, cwd=WORKFLOW, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            record = {"tag": tag, "command": list(map(str, command)), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            record = {"tag": tag, "command": list(map(str, command)), "returncode": None, "status": "timed_out"}
        record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        commands.append(record)
        write(run_dir / f"{tag}.json", record)
        print(f"{tag}: exit={record['returncode']}", flush=True)
        return record

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node missing")
    rebuild = run_dir / "rebuild"
    rebuild.mkdir()
    generator = snapshot / "03-示例与验收" / "make_demo_zh.js"
    shutil.copy2(generator, rebuild / generator.name)
    generation = run("generate", [node, str(rebuild / generator.name)])
    legacy = snapshot / "02-工具链"
    original = snapshot / "03-示例与验收" / "demo-zh.pptx"
    generated = rebuild / "demo-zh.pptx"
    for label, deck in [("original", original), ("rebuilt", generated)]:
        if deck.exists():
            run(f"{label}-lint", [sys.executable, str(legacy / "deck_lint.py"), str(deck), "--json", str(run_dir / f"{label}-lint-report.json")])
            run(f"{label}-structure", [sys.executable, str(legacy / "deck_tools.py"), "check", str(deck)])
            run(f"{label}-content", [sys.executable, str(legacy / "deck_tools.py"), "dump", str(deck)])
    tests = run("contract-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    from pptx import Presentation
    deck_info = {}
    if generated.exists():
        prs = Presentation(generated)
        deck_info = {"path": str(generated), "sha256": sha(generated), "slides": len(prs.slides), "size_in": [round(prs.slide_width / 914400, 3), round(prs.slide_height / 914400, 3)]}
    dependencies = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        license_files = [{"path": str(dist.locate_file(f)), "sha256": sha(Path(dist.locate_file(f)))} for f in dist.files or [] if "license" in str(f).lower() and Path(dist.locate_file(f)).is_file()]
        dependencies.append({"name": name, "version": dist.version, "license_expression": dist.metadata.get("License-Expression"), "license_label": (dist.metadata.get("License") or "").splitlines()[0][:160] if dist.metadata.get("License") else None, "license_files": license_files})
    node_lock = json.loads((WORKFLOW / "package-lock.json").read_text(encoding="utf-8"))
    node_deps = [{"path": name, "version": package.get("version"), "license": package.get("license"), "integrity": package.get("integrity")} for name, package in node_lock["packages"].items() if name]
    fonts = []
    font_root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ["msyh.ttc", "msyhbd.ttc", "calibri.ttf", "calibrib.ttf", "arial.ttf", "arialbd.ttf"]:
        path = font_root / name
        fonts.append({"path": str(path), "installed": path.is_file(), "sha256": sha(path) if path.is_file() else None})
    write(REVIEW / "dependencies.json", {"python": dependencies, "node": node_deps, "font_files": fonts, "font_redistribution": "not performed"})
    changed = [r["path"] for r in records if sha(ROOT / r["path"]) != r["sha256"]]
    baseline_ok = generation["returncode"] == 0 and tests["returncode"] == 0 and deck_info.get("slides") == 10
    summary = {"created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "run_dir": str(run_dir), "python": {"executable": sys.executable, "version": platform.python_version()}, "node": run("node-version", [node, "--version"])["stdout"].strip(), "snapshot_file_count": len(records), "original_files_changed": changed, "rebuild": deck_info, "baseline_execution_ok": baseline_ok, "legacy_qa_is_not_complete_quality_validation": True, "render_status": "not_attempted", "commands": commands}
    write(REVIEW / "baseline-run.json", summary)
    print(json.dumps({"run_dir": str(run_dir), "baseline_execution_ok": baseline_ok, "changed_originals": changed}, ensure_ascii=False))
    return 0 if baseline_ok and not changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
