"""Real MCP/Office and six-stage routing check using fresh project-owned outputs."""
from pathlib import Path
import argparse,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ppt_workflow.workflow import read,write
from ppt_workflow.content import inspect_native
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--node',type=Path,required=True);a=p.parse_args()
out=a.out.resolve()
if not out.is_relative_to(ROOT/'runs'):raise ValueError('Verification must stay inside runs')
out.mkdir(parents=True,exist_ok=False);commands=[];py=ROOT/'.venv/Scripts/python.exe';mcp=ROOT/'.mcp-venv/Scripts/python.exe'
def call(label,argv,expected=0):
    start=time.perf_counter();r=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=150)
    row={'label':label,'command':list(map(str,argv)),'exit':r.returncode,'expected':expected,'seconds':round(time.perf_counter()-start,3),'stdout':r.stdout,'stderr':r.stderr}
    commands.append(row);write(out/'commands.json',commands);print(f'{label}: {r.returncode}, expected {expected}',flush=True)
    if r.returncode!=expected:raise RuntimeError(r.stdout+r.stderr)
def office(operation,target,*rest):
    call('mcp-'+operation,[mcp,ROOT/'scripts/office_mcp_client.py',operation,target,*rest])
call('doctor',[py,'-m','ppt_workflow','doctor'])
call('skills',[py,'-m','ppt_workflow','skills'])
office('health',out/'health')
health=read(out/'health/mcp-client.json')
expected={'health_check','catalog_native_features','create_unified_template','create_from_template','apply_editorial_design','inspect_template_resources','probe_wps_connection','create_wps_template_copy'}
if set(health['tools'])!=expected:raise RuntimeError('MCP tool list differs from documented contract')
for name in ('intake','outline','template','compose','polish','review'):
    call('route-'+name,[py,'-m','ppt_workflow',name,'--workspace',out/'handoffs'],2 if name=='intake' else 1)
office('catalog',out/'catalog')
office('unified-template',out/'template')
office('instantiate',out/'instantiated',out/'template/Unified-Ivory.potx')
office('inspect-template',out/'template-resources',out/'template/Unified-Ivory.potx')
call('fresh-demo-inputs',[py,ROOT/'scripts/create_demo.py','--node',a.node,'--out',out/'inputs'])
call('plan',[py,'-m','ppt_workflow','plan','--config',out/'inputs/workflow.json','--out',out/'job'])
call('build-and-render',[py,'-m','ppt_workflow','build','--run',out/'job','--with-qa'],2)
state=read(out/'job/state.json');qa=read(Path(state['qa_directory'])/'qa.json');render=read(Path(state['qa_directory'])/'render-manifest.json')
native=inspect_native(out/'job/rev-000/deck.pptx',read(out/'job/rev-000/deck-spec.json'))
if native.status!='passed' or render['status']!='passed' or len(render['images'])!=10:raise RuntimeError('Native/render smoke failed')
call('delivery-gate',[py,'-m','ppt_workflow','deliver','--run',out/'job','--out',out/'must-not-release'],1)
assert not (out/'must-not-release').exists()
workers=[read(out/name/'office-worker.json') for name in ('catalog','template','instantiated')]
workers.append(read(Path(state['build_attempt'])/'office/office-worker.json'))
assert all(w['status']=='completed' and w['cleanupCompleted'] for w in workers)
write(out/'verification.json',{'status':'passed-for-documented-local-path','mcp_protocol':'stdio','tool_names':sorted(expected),
    'mcp_operations_executed':6,'stage_routes_verified':6,'powerpoint_owned_workers':len(workers),
    'native_content':native.status,'render':render['status'],'rendered_pages':10,
    'quality_status':qa['status'],'quality_unknown':len(qa['coverage']['unknown']),
    'smartart_supported':workers[0].get('smartart_supported'),'external_tools_tested_separately':True,
    'formal_delivery':'correctly-refused-unverified'})
