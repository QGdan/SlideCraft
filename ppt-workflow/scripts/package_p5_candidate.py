from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
TESTED=ROOT/'runs/p5-dist-003/ppt-workflow';LICENSES=ROOT/'runs/p5-licenses-002'
OUT=ROOT.parent/'06-实施与阶段审核/P5-交付固化';OUT.mkdir(exist_ok=True)
files={}
def add(source,target):
    source=Path(source);assert source.is_file();files['ppt-workflow/'+target]=source
def tree(folder,source=None):
    source=Path(source or ROOT/folder)
    for p in source.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':add(p,folder+'/'+p.relative_to(source).as_posix())
for folder in ('ppt_workflow','engine','render','schemas','skills','assets','templates','docs','office-mcp'):tree(folder)
tree('vendor',TESTED/'vendor');tree('licenses',LICENSES)
for name in ('README.md','使用指南.md','THIRD_PARTY_NOTICES.md','requirements.in','requirements.lock.txt','package.json','package-lock.json','skill-routing.json','pip-install-report.json','office-mcp-install-report.json'):
    add(ROOT/name,name)
for name in ('bootstrap.py','create_demo.py','install_skill.py','office_mcp_client.py','smoke.py'):
    add(ROOT/'scripts'/name,'scripts/'+name)
for name in ('brief.json','deck.json','qa.json','demo-report-v1.json'):add(ROOT/'examples'/name,'examples/'+name)
for name in ('test_contracts.py','test_qa.py','test_render.py','test_chart_scale.py','test_bootstrap.py'):add(ROOT/'tests'/name,'tests/'+name)
tree('tests/fixtures')
add(ROOT/'runs/p2-unified-template-003/Unified-Ivory.potx','templates/unified-v3/Unified-Ivory.potx')
manifest=[{'path':path,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size} for path,source in sorted(files.items())]
archive=OUT/'PPT工作流-候选安装包-v0.1.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for target,source in sorted(files.items()):z.write(source,target)
    z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    z.writestr('安装说明.md','此包为Windows x64 / Python3.12本地研究候选，尚非正式发布。进入ppt-workflow阅读使用指南.md；先bootstrap预览与安装，再运行smoke或创建demo。无需网络下载依赖；需本机Python、Node、PowerPoint与字体。六个Skill独立，总控仅调度。公开发布和质量限制见THIRD_PARTY_NOTICES.md。')
with ZipFile(archive) as z:assert z.testzip() is None
record={'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'files':len(manifest),
    'quality_release':'candidate-only','complete_historical_tests_included':False,'portable_tests':77}
(OUT/'candidate-package.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
