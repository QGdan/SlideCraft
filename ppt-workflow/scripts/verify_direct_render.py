"""Verify a directly launched Office worker; never start Office in this process."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ppt_workflow.render import sha256,verify_images,save
from pptx import Presentation

def verify(pptx,out,width,height):
    pptx,out=Path(pptx).resolve(),Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs'):raise ValueError('Project runs directory required')
    target=out/'render-manifest.json'
    if target.exists():raise ValueError('Existing render manifest retained')
    worker=json.loads((out/'powerpoint-worker.json').read_text(encoding='utf-8-sig'))
    process=json.loads((out/'process.json').read_text(encoding='utf-8-sig'))
    count=len(Presentation(pptx).slides)
    if process['returncode']!=0 or process.get('timed_out'):raise ValueError('Direct worker process failed')
    if count<1 or worker.get('status')!='exported' or worker.get('cleanupCompleted') is not True or worker.get('cleanupError'):raise ValueError('Office export or cleanup not completed')
    if worker.get('inputSha256')!=sha256(pptx) or worker.get('slideCount')!=count:raise ValueError('Office evidence does not match input')
    images=verify_images(out/'slides',count,width,height)
    result=dict(status='passed',renderer='powerpoint',launch_route='direct-powershell',input_path=str(pptx),input_sha256=sha256(pptx),expected_slide_count=count,width=width,height=height,images=images,worker=worker,commands=[process],visual_review='not_implied_by_export')
    save(target,result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pptx',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,default=1600);p.add_argument('--height',type=int,default=900);a=p.parse_args()
    r=verify(a.pptx,a.out,a.width,a.height);print(json.dumps(dict(status=r['status'],images=len(r['images']),route=r['launch_route']),ensure_ascii=False))
