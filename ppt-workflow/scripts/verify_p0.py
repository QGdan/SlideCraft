"""Verify P0 handoff evidence without regenerating or rerendering."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent
P0 = PROJECT / "06-实施与阶段审核" / "P0"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = read(P0 / "baseline-manifest.json")
baseline = read(P0 / "baseline-run.json")
render = read(P0 / "render-manifest.json")
tests = read(P0 / "contract-tests-final.json")
state = read(PROJECT / "06-实施与阶段审核" / "阶段状态.json")
changed = [r["path"] for r in manifest["originals"] if sha(PROJECT / r["path"]) != r["sha256"]]
source_match = all(sha(P0 / "snapshot" / r["path"]) == r["sha256"] for r in manifest["originals"])
images_match = all(Path(r["path"]).is_file() and sha(Path(r["path"])) == r["sha256"] and r["size_px"] == [1600,900] for r in render["image_validation"])
content_commands = {r["tag"]: r for r in baseline["commands"] if "content" in r["tag"]}
content_match = content_commands["original-content"]["stdout"] == content_commands["rebuilt-content"]["stdout"]
from ppt_workflow.contracts import validate, validate_bundle
examples = {k: read(ROOT / "examples" / f"{k}.json") for k in ["brief", "deck", "qa"]}
contract_errors = {k: validate(v, k) for k,v in examples.items()}
contract_errors["bundle"] = validate_bundle(examples["brief"],examples["deck"])
result = {
    "original_file_count": len(manifest["originals"]), "changed_originals": changed,
    "snapshot_matches": source_match, "rebuild_content_matches_original": content_match,
    "rebuilt_deck_hash_matches": sha(Path(baseline["rebuild"]["path"])) == baseline["rebuild"]["sha256"],
    "rendered_input_matches_rebuilt": render["inputSha256"] == baseline["rebuild"]["sha256"],
    "images_verified": images_match and len(render["image_validation"]) == 10,
    "contract_tests_passed": tests["returncode"] == 0 and "Ran 18 tests" in tests["stderr"],
    "contract_errors": contract_errors,
    "p0_awaiting_user_review": state["stages"]["P0"]["review"] == "awaiting_user",
    "later_stages_not_started": all(state["stages"][k]["implementation"] == "not_started" for k in ["P1","P2","P3","P4","P5"])
}
result["passed"] = not changed and source_match and content_match and result["rebuilt_deck_hash_matches"] and result["rendered_input_matches_rebuilt"] and result["images_verified"] and result["contract_tests_passed"] and not any(contract_errors.values()) and result["p0_awaiting_user_review"] and result["later_stages_not_started"]
(P0 / "final-verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result["passed"] else 1)
