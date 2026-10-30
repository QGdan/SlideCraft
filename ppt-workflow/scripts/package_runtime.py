"""Build a current offline package without modifying historical review archives."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--dependencies',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out.resolve()
if not out.is_relative_to(ROOT.parent) or out.exists():raise ValueError('Fresh project-local archive required')
out.parent.mkdir(parents=True,exist_ok=True);files={}
def add(path,target):files['ppt-workflow/'+target]=Path(path).read_bytes()
for folder in ('ppt_workflow','engine','render','schemas','skills','templates','assets','docs','office-mcp'):
    for f in (ROOT/folder).rglob('*'):
        if folder=='assets' and 'online-cache' in f.relative_to(ROOT/folder).parts:continue
        if folder=='templates' and 'imported' in f.relative_to(ROOT/folder).parts and f.name!='README.md':continue
        if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':add(f,f.relative_to(ROOT).as_posix())
for name in ('README.md','使用指南.md','THIRD_PARTY_NOTICES.md','package.json','package-lock.json','requirements.in','requirements.lock.txt','pip-install-report.json','office-mcp-install-report.json','skill-routing.json'):
    add(ROOT/name,name)
for name in ('bootstrap.py','create_demo.py','install_skill.py','office_mcp_client.py','smoke.py','verify_connections.py','verify_project_upgrade.py','verify_effects.py','probe_wps.py','verify_wps_editing.py','verify_wps_elements.py','render_direct.ps1','verify_direct_render.py','activate_wps.ps1'):
    add(ROOT/'scripts'/name,'scripts/'+name)
for name in ('brief.json','deck.json','qa.json','demo-report-v1.json','quality-outline.json','content-plan.json','campus-blueprint.json','campus-blueprint-ink.json','layout-comparison.json','module-request.json','chart-demo-source.json','chart-style-focus-comparison.json','chart-style-series-comparison.json','chart-style-focus-trend.json'):add(ROOT/'examples'/name,'examples/'+name)
portable_modules=('test_contracts.py','test_qa.py','test_render.py','test_chart_scale.py','test_bootstrap.py','test_mcp_client.py','test_template_resources.py','test_wps_bridge.py','test_quality.py','test_chart_compile.py','test_exhibits.py','test_blueprints.py','test_visual_assets.py','test_icon_library.py','test_direct_render.py','test_scene_modules.py','test_chart_styles.py','test_online_assets.py','test_production_materials.py','test_editorial_design.py')
for name in portable_modules:add(ROOT/'tests'/name,'tests/'+name)
for f in (ROOT/'tests/fixtures').rglob('*'):
    if f.is_file():add(f,f.relative_to(ROOT).as_posix())
with ZipFile(a.dependencies) as old:
    original={r['path']:r for r in json.loads(old.read('manifest.json'))}
    for name in old.namelist():
        if not name.startswith(('ppt-workflow/vendor/','ppt-workflow/licenses/')):continue
        data=old.read(name)
        if hashlib.sha256(data).hexdigest()!=original[name]['sha256']:raise ValueError('Dependency archive hash mismatch: '+name)
        files[name]=data
if 'ppt-workflow/templates/unified-v3/Unified-Ivory.potx' not in files:
    add(ROOT/'runs/p2-unified-template-003/Unified-Ivory.potx','templates/unified-v3/Unified-Ivory.potx')
manifest=[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())]
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for name,data in sorted(files.items()):z.writestr(name,data)
    z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    z.writestr('安装说明.md','本地试用整理版，包含quality-v1工程升级。进入ppt-workflow阅读使用指南.md与docs/质量升级工作流.md。Windows x64 / Python3.12，需本机Node、PowerPoint及字体。bootstrap离线安装后运行smoke，以其实际测试报告为准。会员下载模板不包含在包内。此包不是已清除全部质量unknown的公开发行版。')
with ZipFile(out) as z:assert z.testzip() is None
proof={'archive':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(manifest),'portable_test_modules':list(portable_modules),'test_count':'see actual smoke report','source_dependencies':str(a.dependencies.resolve())}
out.with_suffix('.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(proof,ensure_ascii=False))
