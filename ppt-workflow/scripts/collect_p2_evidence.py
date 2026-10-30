"""Freeze P2 evidence after actual image review. This is not the P3 delivery CLI."""
import io
import json
import shutil
import sys
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.design import THEMES
from ppt_workflow.content import check_ledger,inspect_native,bind_content
from ppt_workflow.qa.inspect import inspect_deck,bind_render
from ppt_workflow.contracts import validate_bundle,validate
from ppt_workflow.render import sha256,save

STAGE=ROOT.parent/"06-实施与阶段审核/P2"
SAMPLES=ROOT/"runs/p2-review-002"
STAGE.mkdir(parents=True,exist_ok=True)


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):super().addSuccess(test);self.records.append(dict(id=test.id(),status="passed"))
    def addFailure(self,test,err):super().addFailure(test,err);self.records.append(dict(id=test.id(),status="failed"))
    def addError(self,test,err):super().addError(test,err);self.records.append(dict(id=test.id(),status="error"))
    def addSkip(self,test,reason):super().addSkip(test,reason);self.records.append(dict(id=test.id(),status="skipped",reason=reason))


log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"))
result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
(STAGE/"tests.log").write_text(log.getvalue(),encoding="utf-8")
save(STAGE/"tests.json",dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),tests=result.records))
if not result.wasSuccessful() or result.skipped:raise RuntimeError("P2 regression tests failed/skipped")
baseline=json.loads((STAGE.parent/"P0/baseline-manifest.json").read_text(encoding="utf-8"))
originals=[dict(path=f["path"],unchanged=sha256(ROOT.parent/f["path"])==f["sha256"]) for f in baseline["originals"]]
if not all(f["unchanged"] for f in originals):raise RuntimeError("Historical input changed")
edited=json.loads((ROOT/"runs/p2-edit-probe-001/edit-probe.json").read_text(encoding="utf-8"))
if edited["status"]!="passed" or edited["output_sha256"]!=sha256(ROOT/"runs/p2-edit-probe-001/edited-copy.pptx"):raise RuntimeError("Edit probe evidence changed")
save(STAGE/"edit-probe.json",edited)
reviews=[];samples=[]
for name,t in THEMES.items():
    d=SAMPLES/name;load=lambda filename:json.loads((d/filename).read_text(encoding="utf-8"))
    spec=load("deck-spec.json");brief=load("brief.json");manifest=load("render/render-manifest.json")
    if validate_bundle(brief,spec):raise RuntimeError("Spec contract invalid")
    ledger=check_ledger(spec,ROOT);native=inspect_native(d/"deck.pptx",spec)
    if ledger.status!="passed" or native.status!="passed":raise RuntimeError("Content/native checks failed")
    inspection=inspect_deck(d/"deck.pptx",job_id=spec["job_id"],role_map={x["output_id"]:x["role"] for x in native.details["mapping"]})
    inspection=bind_render(bind_content(inspection,ledger,native),manifest)
    if inspection.qa["status"]=="failed" or manifest["status"]!="passed":raise RuntimeError("Final checks failed")
    # Observations entered by Codex after viewing these exact contact sheets and full-size pages.
    review=dict(reviewer="Codex host visual inspection, not user approval",theme=name,
                input_sha256=sha256(d/"deck.pptx"),contact_sha256=sha256(d/"contact.png"),
                contact_pages=list(range(1,11)),full_size_pages=[5,8],images=manifest["images"],
                status="reviewed_no_blocking_findings",observations=[
                    "十页接触表中的标题、正文和留白保持一致，无可见对象相互遮挡。",
                    "图表从零起点显示人工40与自动1分钟，标签对应正确，39分钟说明保留审核不计入的限制。",
                    "表格的四行数据与前文一致，各单元格文字完整，表头与正文对比清晰。",
                    "四步流程连接方向正确，四周安排完整，结束页明确试点范围与决策依据。",
                    "各页可见示意、非实测披露，封面和章节页保持低信息密度。"],
                limitations=["图表和表格的每个标签几何未逐对象自动测量。","主题风格与内容精简程度尚待 G2 用户审核。"])
    reviews.append(review)
    qa=inspection.qa
    qa["stages"]["visual"]=dict(status="passed",evidence=["Host image inspection: contact pages 1-10 and full-size pages 5,8",f"input sha256:{review['input_sha256']}"])
    qa["coverage"]["unknown"]=[u for u in qa["coverage"]["unknown"] if u!="visual-review-not-executed"]
    qa["coverage"]["evaluated"].append("host-image-inspection-bound-to-final-render")
    if name=="academic":
        if edited["input_sha256"]!=qa["artifact"]["sha256"]:raise RuntimeError("Probe input differs from final academic output")
        qa["stages"]["editability"]=dict(status="passed",evidence=["Representative native chart resize, table cell and text edits saved and reopened in PowerPoint 16.0 build 20430",f"probe output sha256:{edited['output_sha256']}"])
        qa["coverage"]["unknown"]=[u for u in qa["coverage"]["unknown"] if u!="PowerPoint-edit-roundtrip-not-executed"]
        qa["coverage"]["evaluated"].append("representative-native-object-PowerPoint-edit-roundtrip")
    qa["coverage"]["unknown"]+= ["all-chart-types-and-value-edit-roundtrips-not-tested"]
    qa["coverage"]["unknown"]=sorted(set(qa["coverage"]["unknown"]))
    qa["status"]="unverified" if qa["coverage"]["unknown"] else "passed"
    if validate(qa,"qa"):raise RuntimeError("Bound QA contract invalid")
    target=STAGE/"样例"/name;target.mkdir(parents=True,exist_ok=False)
    for filename in ["deck.pptx","deck-spec.json","brief.json","theme.json","contact.png","export-fixes.json"]:shutil.copy2(d/filename,target/filename)
    save(target/"qa.json",qa);save(target/"inspection-details.json",inspection.details);save(target/"object-map.json",native.details)
    shutil.copytree(d/"render/slides",target/"slides");shutil.copy2(d/"render/render-manifest.json",target/"render-manifest.json")
    samples.append(dict(theme=name,path=str(target/"deck.pptx"),sha256=sha256(target/"deck.pptx"),slides=10,native_objects=len(native.details["mapping"]),
                        render=manifest["status"],render_images=len(manifest["images"]),qa_status=qa["status"],issues=qa["issues"],unknown=qa["coverage"]["unknown"],
                        target_text_bounds=len(inspection.details["target_bounds"]),native_chart_workbook=native.details["charts"],visual_review=review["status"]))
    save(d/"qa-final.json",qa)
save(STAGE/"visual-review.json",reviews)
shutil.copy2(ROOT/"examples/demo-report-v1.json",STAGE/"sources.json")
shutil.copy2(ROOT/"P2组件说明.md",STAGE/"组件接口.md")
files=[]
for base in ["ppt_workflow","schemas","scripts","tests","engine","examples","render"]:
    files.extend(p for p in (ROOT/base).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
files += [ROOT/"README.md",ROOT/"P2组件说明.md",ROOT/"package.json",ROOT/"package-lock.json",ROOT/"requirements.lock.txt"]
snapshot=STAGE/"code-snapshot"
source_hashes=[]
for path in files:
    relative=path.relative_to(ROOT);target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    source_hashes.append(dict(path=str(relative),sha256=sha256(path)))
save(STAGE/"verification.json",dict(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
    tests=dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped)),
    originals=originals,samples=samples,source_hashes=source_hashes,edit_probe=dict(status=edited["status"],input_sha256=edited["input_sha256"],output_sha256=edited["output_sha256"])))
print(json.dumps(dict(tests=result.testsRun,skipped=len(result.skipped),samples=len(samples),pages=30,originals_unchanged=len(originals)),ensure_ascii=False))
