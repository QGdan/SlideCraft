"""Freeze revision evidence after reviewing all final PowerPoint screenshots."""
import io
import json
import shutil
import sys
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.unified import unified_deck,check_unified_consistency,PROFILE
from ppt_workflow.content import inspect_native,check_ledger
from ppt_workflow.render import sha256,save

OUT=ROOT.parent/"06-实施与阶段审核/P2-统一模板修订"
OFFICE=ROOT/"runs/p2-unified-office-003";SAMPLE=ROOT/"runs/p2-unified-content-003";TEMPLATE=ROOT/"runs/p2-unified-template-003";ART=ROOT/"runs/p2-unified-editable-002"
OUT.mkdir(parents=True,exist_ok=True)


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.records=[]
    def addSuccess(self,t):super().addSuccess(t);self.records.append(dict(id=t.id(),status="passed"))
    def addError(self,t,e):super().addError(t,e);self.records.append(dict(id=t.id(),status="error"))
    def addFailure(self,t,e):super().addFailure(t,e);self.records.append(dict(id=t.id(),status="failed"))
    def addSkip(self,t,reason):super().addSkip(t,reason);self.records.append(dict(id=t.id(),status="skipped",reason=reason))


log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(unittest.defaultTestLoader.discover(str(ROOT/"tests")))
(OUT/"tests.log").write_text(log.getvalue(),encoding="utf-8")
save(OUT/"tests.json",dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),cases=result.records))
if not result.wasSuccessful() or result.skipped:raise RuntimeError("Regression tests failed or skipped")
deck,design=unified_deck();consistency=check_unified_consistency(deck,OFFICE/"deck.pptx")
assert consistency.status=="passed",consistency.issues
assert inspect_native(OFFICE/"deck.pptx",deck).status=="passed" and check_ledger(deck,ROOT).status=="passed"
save(OUT/"consistency.json",dict(status=consistency.status,evaluated=consistency.evaluated,issues=consistency.issues,details=consistency.details))
render=json.loads((OFFICE/"render/render-manifest.json").read_text(encoding="utf-8"))
assert render["status"]=="passed" and len(render["images"])==10 and render["input_sha256"]==sha256(OFFICE/"deck.pptx")
for x in render["images"]:assert sha256(x["path"])==x["sha256"]
qa=json.loads((OFFICE/"qa.json").read_text(encoding="utf-8"));assert not qa["issues"]
qa["stages"]["visual"]=dict(status="passed",evidence=["Viewed all 10 final full-size PNGs and contact sheet",f"deck sha256:{sha256(OFFICE/'deck.pptx')}"])
qa["coverage"]["unknown"]=[u for u in qa["coverage"]["unknown"] if u!="visual-review-not-executed"]
qa["coverage"]["evaluated"]+=consistency.evaluated
save(OUT/"qa.json",qa)
copies=[(OFFICE/"deck.pptx","统一模板版-教学报告.pptx"),(TEMPLATE/"Unified-Ivory.potx","统一暖白青绿模板.potx"),(OFFICE/"contact.png","十页接触表.png"),
        (ART/"editable-components.pptx","可编辑图形模块.pptx"),(ART/"report-review-editable.svg","报告与审核-可编辑.svg"),(ART/"editable-nodes.json","editable-nodes.json"),
        (ART/"worker.json","editable-art-evidence.json"),(ART/"render/slides/slide-001.png","可编辑模块预览.png"),
        (SAMPLE/"deck-spec.json","deck-spec.json"),(SAMPLE/"brief.json","brief.json"),(SAMPLE/"template-profile.json","template-profile.json"),
        (PROFILE,"design-system.json"),(TEMPLATE/"mcp-client.json","template-first-mcp.json"),(TEMPLATE/"office-worker.json","template-first-office.json"),
        (OFFICE/"mcp-client.json","content-mcp.json"),(OFFICE/"office-worker.json","content-office.json"),
        (OFFICE/"object-map.json","object-map.json"),(OFFICE/"inspection-details.json","inspection-details.json"),(OFFICE/"render/render-manifest.json","render-manifest.json")]
for source,name in copies:shutil.copy2(source,OUT/name)
shutil.copytree(OFFICE/"render/slides",OUT/"slides",dirs_exist_ok=True)
shutil.copytree(ROOT/"assets/unified-v3",OUT/"素材与提示词",dirs_exist_ok=True)
shutil.copy2(ROOT/"assets/editorial-v2/prompts.json",OUT/"素材与提示词/复用素材原始提示词.json")
comparison=Image.new("RGB",(1600,1350),"white")
old=ROOT/"runs/p2-editorial-office-004/render/slides"
for row,num in enumerate(["001","003","009"]):
    for col,path in enumerate([old/f"slide-{num}.png",OFFICE/f"render/slides/slide-{num}.png"]):
        with Image.open(path) as im:comparison.paste(im.resize((800,450),Image.Resampling.LANCZOS),(col*800,row*450))
comparison.save(OUT/"跨页一致性对照.png")
baseline=json.loads((OUT.parent/"P0/baseline-manifest.json").read_text(encoding="utf-8"));originals=[dict(path=f["path"],unchanged=sha256(ROOT.parent/f["path"])==f["sha256"]) for f in baseline["originals"]]
assert all(o["unchanged"] for o in originals)
save(OUT/"visual-review.json",dict(reviewer="Codex host image review; user approval pending",full_size_pages=list(range(1,11)),images=render["images"],input_sha256=sha256(OFFICE/"deck.pptx"),
    observations=["十页共用暖白背景与标题/页脚坐标。","封面图片已改为浅色环境并放入内容区，章节页保持同一标题体系。","正文、数字、流程与表格沿用统一字体与青绿强调色。","已逐页查看原图，没有发现阻断性的遮挡或截断。","可编辑模块为原生语义重建，保留12个可修改子对象；不声称还原原图的材质细节。"],status="reviewed_no_blocking_findings"))
hashes=[]
for folder in ["ppt_workflow","schemas","scripts","tests","engine","render","office-mcp","templates/unified-v3","assets/unified-v3"]:
    for p in (ROOT/folder).rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:continue
        rel=p.relative_to(ROOT);dest=OUT/"code-snapshot"/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes.append(dict(path=str(rel),sha256=sha256(p)))
save(OUT/"verification.json",dict(date="2026-10-16",tests=dict(run=result.testsRun,failed=len(result.failures)+len(result.errors),skipped=len(result.skipped)),source_hashes=hashes,originals=originals,
    template_created_before_content=True,template_sha256=sha256(TEMPLATE/"Unified-Ivory.potx"),design_sha256=sha256(PROFILE),render_images=10,consistency_status=consistency.status,
    deliverables=[dict(path=name,sha256=sha256(OUT/name)) for name in ["统一模板版-教学报告.pptx","统一暖白青绿模板.potx","可编辑图形模块.pptx","报告与审核-可编辑.svg"]]))
state_path=OUT.parent/"阶段状态.json";state=json.loads(state_path.read_text(encoding="utf-8"));state["date"]="2026-10-16"
state["stages"]["P2"].update(implementation="completed",review="awaiting_user",revision="unified-v3",report="P2-统一模板修订/统一模板审核.md",feedback_resolved="已先创建统一模板并冻结哈希，再应用正式内容；新增一致性检查与原生可编辑重建模块。Figma当前未提供可调用工具。")
save(state_path,state)
print(json.dumps(dict(tests=result.testsRun,failed=len(result.errors)+len(result.failures),skipped=len(result.skipped),consistency=consistency.status,output=str(OUT)),ensure_ascii=False))
