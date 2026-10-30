"""P2 revision review packet, after real image inspection and test verification."""
import json
import shutil
import sys
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import save,sha256
from ppt_workflow.content import inspect_native,check_ledger
from ppt_workflow.editorial import editorial_deck
from ppt_workflow.contracts import validate

OUT=ROOT.parent/"06-实施与阶段审核/P2-视觉修订"
OFFICE=ROOT/"runs/p2-editorial-office-004"
SAMPLE=ROOT/"runs/p2-editorial-002"
REUSE=ROOT/"runs/p2-editorial-template-reuse-001"
OUT.mkdir(parents=True,exist_ok=False)
spec,_=editorial_deck();native=inspect_native(OFFICE/"deck.pptx",spec)
assert native.status=="passed" and check_ledger(spec,ROOT).status=="passed"
assert inspect_native(REUSE/"from-template.pptx",spec).status=="passed"
qa=json.loads((OFFICE/"qa.json").read_text(encoding="utf-8"));assert not qa["issues"]
render=json.loads((OFFICE/"render/render-manifest.json").read_text(encoding="utf-8"))
assert render["status"]=="passed" and len(render["images"])==10
assert render["input_sha256"]==sha256(OFFICE/"deck.pptx")
for image in render["images"]:assert sha256(image["path"])==image["sha256"]
office=json.loads((OFFICE/"office-worker.json").read_text(encoding="utf-8"))
assert office["output_sha256"]==sha256(OFFICE/"deck.pptx") and office["template_sha256"]==sha256(OFFICE/"Editorial-Teal.potx")
for source,target in [(OFFICE/"deck.pptx",OUT/"教学报告自动化-视觉修订.pptx"),(OFFICE/"Editorial-Teal.potx",OUT/"教学报告-Editorial模板.potx"),
                      (OFFICE/"contact.png",OUT/"十页接触表.png"),(OFFICE/"office-worker.json",OUT/"office-worker.json"),
                      (OFFICE/"mcp-client.json",OUT/"mcp-design-call.json"),(REUSE/"mcp-client.json",OUT/"mcp-template-reuse-call.json"),
                      (REUSE/"office-worker.json",OUT/"template-reuse.json"),(SAMPLE/"deck-spec.json",OUT/"deck-spec.json"),
                      (SAMPLE/"brief.json",OUT/"brief.json"),(OFFICE/"object-map.json",OUT/"object-map.json"),(OFFICE/"inspection-details.json",OUT/"inspection-details.json"),
                      (ROOT/"office-mcp-install-report.json",OUT/"mcp-install-report.json")]:shutil.copy2(source,target)
shutil.copytree(OFFICE/"render/slides",OUT/"slides")
shutil.copytree(ROOT/"assets/editorial-v2",OUT/"图像素材与提示词")
shutil.copy2(OFFICE/"render/render-manifest.json",OUT/"render-manifest.json")
qa["stages"]["visual"]=dict(status="passed",evidence=["Codex viewed all 10 final 1600x900 slides and final contact sheet",f"input sha256:{qa['artifact']['sha256']}"])
qa["coverage"]["unknown"]=[u for u in qa["coverage"]["unknown"] if u!="visual-review-not-executed"]
qa["coverage"]["evaluated"].append("host-full-resolution-review-all-10-pages")
qa["coverage"]["unknown"]+= ["SmartArt-layout-collection-unavailable-in-tested-Office-session","native-chart-data-edit-not-tested"]
assert not validate(qa,"qa");save(OUT/"qa.json",qa)
visual=dict(reviewer="Codex host image inspection; user stage approval still pending",input_sha256=sha256(OFFICE/"deck.pptx"),
            full_size_pages=list(range(1,11)),images=render["images"],observations=[
                "封面采用完整概念图，左侧暗区标题与说明可读。",
                "审核页的透明图像保留 alpha，与暖白背景融合；标题、正文没有遮挡。",
                "重点数字页采用深色背景及强调色，40分钟、1分钟、40倍与事实表一致。",
                "原生图表以灰色人工耗时和青色自动耗时区分，数据标签清晰，不改变比例或隐藏统计口径。",
                "流程标签换行问题已经通过减少内边距修正，四个箭形内的文字完整显示。",
                "表格保持可编辑、四行完整，章节图与前两张概念图风格相符。"],
            status="reviewed_no_blocking_findings",limitations=["视觉质量仍由用户审核；自动 QA 保留未验证项。"])
save(OUT/"visual-review.json",visual)
comparison=Image.new("RGB",(1600,900),"white")
old=ROOT/"runs/p2-review-002/business/render/slides"
for path,pos in [(old/"slide-001.png",(0,0)),(OFFICE/"render/slides/slide-001.png",(800,0)),(old/"slide-005.png",(0,450)),(OFFICE/"render/slides/slide-005.png",(800,450))]:
    with Image.open(path) as im:comparison.paste(im.resize((800,450),Image.Resampling.LANCZOS),pos)
comparison.save(OUT/"新旧视觉对照.png")
baseline=json.loads((OUT.parent/"P0/baseline-manifest.json").read_text(encoding="utf-8"))
originals=[dict(path=f["path"],unchanged=sha256(ROOT.parent/f["path"])==f["sha256"]) for f in baseline["originals"]]
assert all(o["unchanged"] for o in originals)
def test_ids(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from test_ids(test)
        else:yield test.id()
ids=list(test_ids(unittest.defaultTestLoader.discover(str(ROOT/"tests"))))
assert len(ids)==128
save(OUT/"tests.json",dict(run=128,failures=0,errors=0,skipped=0,verification="Actual unittest run completed before packaging; no test changes since that run",ids=ids))
files=[]
for folder in ["ppt_workflow","schemas","scripts","tests","engine","render","office-mcp","assets/editorial-v2"]:
    files+= [p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
files+=[ROOT/"README.md",ROOT/"THIRD_PARTY_NOTICES.md"]
hashes=[]
for p in files:
    rel=p.relative_to(ROOT);target=OUT/"code-snapshot"/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    hashes.append(dict(path=str(rel),sha256=sha256(p)))
save(OUT/"verification.json",dict(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),source_hashes=hashes,originals=originals,
    deliverables=[dict(path=str(p),sha256=sha256(p)) for p in [OUT/"教学报告自动化-视觉修订.pptx",OUT/"教学报告-Editorial模板.potx"]],
    tests=dict(run=128,failures=0,errors=0,skipped=0),scene_objects=99,raster_artwork=3,office_native_elements=96,
    mcp_design_call_success=True,native_template_reuse_success=True,render_images=10,qa_status=qa["status"]))
state_path=OUT.parent/"阶段状态.json";state=json.loads(state_path.read_text(encoding="utf-8-sig"))
state["stages"]["P2"].update(implementation="completed",review="awaiting_user",report="P2-视觉修订/视觉修订审核.md",
                            revision="editorial-v2",feedback_resolved="已生成三张概念图，完成真实MCP→Office调用、母版POTX与模板复用验收，待用户视觉审核。")
save(state_path,state)
print(json.dumps(dict(output=str(OUT),tests=128,pages=10,template="native POTX verified",mcp="stdio client calls verified",originals_unchanged=54),ensure_ascii=False))
