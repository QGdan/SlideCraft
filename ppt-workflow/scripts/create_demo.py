"""Create fresh project-relative demo inputs; never grants business-content approval."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ppt_workflow.unified import unified_deck,PROFILE
from ppt_workflow.workflow import write,sha256
def main():
    p=argparse.ArgumentParser();p.add_argument('--node',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Demo inputs must stay inside this runtime')
    node=a.node.resolve()
    if not node.is_file():raise ValueError('Node executable missing')
    template=ROOT/'templates/unified-v3/Unified-Ivory.potx'
    if not template.is_file():template=ROOT/'runs/p2-unified-template-003/Unified-Ivory.potx'
    if not template.is_file():raise ValueError('Packaged unified template missing')
    out.mkdir(parents=True,exist_ok=False);spec,_=unified_deck()
    spec['job_id']='packaged-unified-demo'
    brief=dict(schema_version='0.1',job_id=spec['job_id'],topic='教学报告自动化示意',audience='教研组',language='zh-CN',
        delivery_mode='presented',slide_count=10,aspect_ratio='16:9',sources=spec['sources'],
        required_native_types=['text','chart','table','diagram'],theme='business')
    write(out/'deck-spec.json',spec);write(out/'brief.json',brief)
    write(out/'workflow.json',{'spec':'deck-spec.json','brief':'brief.json',
        'template':str(template),'design_system':str(PROFILE),'node':str(node),'renderer':'powerpoint',
        'design_approval':{'spec_sha256':sha256(out/'deck-spec.json'),'template_sha256':sha256(template),
            'design_sha256':sha256(PROFILE),'reviewer':'agent-functional-probe',
            'evidence':'Synthetic installation demo only; not human approval of business content or release.'}})
    print(json.dumps({'status':'created','config':str(out/'workflow.json'),'demo_only':True},ensure_ascii=False))
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');main()
