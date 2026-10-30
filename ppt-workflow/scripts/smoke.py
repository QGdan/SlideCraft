"""Portable test subset; historic integration evidence stays in the research project."""
from pathlib import Path
import argparse,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser();p.add_argument('--node',type=Path,required=True);a=p.parse_args()
os.environ['PPT_WORKFLOW_NODE']=str(a.node.resolve())
(ROOT/'runs').mkdir(exist_ok=True)
names=['test_contracts.py','test_qa.py','test_render.py','test_chart_scale.py','test_bootstrap.py','test_mcp_client.py','test_template_resources.py','test_wps_bridge.py','test_quality.py','test_chart_compile.py','test_exhibits.py','test_blueprints.py','test_visual_assets.py','test_icon_library.py','test_direct_render.py','test_scene_modules.py','test_chart_styles.py','test_online_assets.py','test_production_materials.py','test_editorial_design.py']
suite=unittest.TestSuite()
for name in names:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=name))
result=unittest.TextTestRunner(verbosity=1).run(suite)
report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skipped':len(result.skipped),'test_modules':names,'scope':'portable deterministic subset, not full historical integration or visual acceptance',
    'passed':result.wasSuccessful() and not result.skipped}
(ROOT/'runs/portable-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if report['passed'] else 1)
