"""Bounded P0 COM attempt and exported-image verification."""
from datetime import datetime, timezone, timedelta
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
parser = argparse.ArgumentParser()
parser.add_argument("--attempt", type=int, default=2)
args = parser.parse_args()
REVIEW = ROOT.parent / "06-实施与阶段审核" / "P0"
RUN = ROOT / "runs" / "p0-20261014-001"
REPORT = REVIEW / "render-manifest.json"
attempt_path = REVIEW / f"render-attempt-{args.attempt}.json"
if attempt_path.exists():
    raise RuntimeError("Attempt evidence already exists; use a new attempt number")
command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "render_baseline.ps1"), "-Pptx", str(RUN / "rebuild" / "demo-zh.pptx"), "-OutDir", str(RUN / "rendered"), "-Report", str(REPORT)]
started = time.perf_counter()
result = {"attempt": args.attempt, "timeout_seconds": 60, "command": command, "started_at": datetime.now(timezone(timedelta(hours=8))).isoformat()}
try:
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    result.update(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)
except subprocess.TimeoutExpired:
    result.update(returncode=None, status="timed_out", note="Only this invocation's PowerShell helper was terminated; no global PowerPoint process kill.")
result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
attempt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
manifest = json.loads(REPORT.read_text(encoding="utf-8-sig")) if REPORT.exists() else {"status": "unverified", "renderer": "PowerPoint COM", "error": "PowerShell did not produce a manifest", "slides": []}
valid = result.get("returncode") == 0
if valid:
    files = sorted((RUN / "rendered").glob("slide-*.png"))
    valid = len(files) == 10 and len(manifest.get("slides", [])) == 10
    verified = []
    for path in files:
        with Image.open(path) as image:
            image.load()
            size = list(image.size)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        valid = valid and size == [1600, 900]
        verified.append({"path": str(path), "sha256": digest, "size_px": size})
    recorded = {r["path"]: r["sha256"] for r in manifest.get("slides", [])}
    valid = valid and all(recorded.get(r["path"]) == r["sha256"] for r in verified)
    manifest["image_validation"] = verified
manifest["status"] = "rendered_and_image_verified" if valid else "unverified"
manifest["attempt"] = result
REPORT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
baseline = json.loads((REVIEW / "baseline-run.json").read_text(encoding="utf-8"))
baseline["render_status"] = manifest["status"]
(REVIEW / "baseline-run.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"render_status": manifest["status"], "error": manifest.get("error"), "returncode": result.get("returncode"), "slide_images": len(manifest.get("slides", []))}, ensure_ascii=False))
raise SystemExit(0 if valid else 2)
