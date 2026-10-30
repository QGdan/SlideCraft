"""Validated editorial compilation through the existing narrow export normalizer."""
from pathlib import Path
import subprocess
from .online_assets import ROOT,local,fresh,read,write
from .contracts import validate
from .assets import check_assets
from .content import inspect_native,check_ledger
from .export_fix import normalize
from .qa.package import check_package

def build_editorial(input_path,out,node,design=None):
    source=local(input_path);out=fresh(out);spec=read(source)
    errors=validate(spec,'deck')
    if errors:raise ValueError('Invalid editorial spec: '+str(errors[:3]))
    if any(e['type'] in ('diagram','smartart') for page in spec['slides'] for e in page['elements']):
        raise ValueError('Editorial compiler requires expanded native objects: use relationship-prepare; SmartArt uses the supported Office route')
    assets=check_assets(spec);ledger=check_ledger(spec,ROOT)
    if assets.issues or ledger.issues:raise ValueError('Editorial source/asset checks failed: '+str(assets.issues+ledger.issues)[:800])
    design=local(design) if design else None
    out.mkdir(parents=True)
    args=[str(node),str(ROOT/'engine/editorial_build.cjs'),str(source),str(out/'raw.pptx')]
    if design:args.append(str(design))
    try:subprocess.run(args,cwd=ROOT,check=True,capture_output=True,timeout=60)
    except (subprocess.SubprocessError,OSError) as exc:raise RuntimeError('Editorial compiler failed; output is not deliverable') from exc
    structured=any(e.get('group_id') or e.get('connection') for page in spec['slides'] for e in page['elements'])
    normalization=normalize(out/'raw.pptx',out/('normalized.pptx' if structured else 'candidate.pptx'));write(out/'normalization.json',normalization)
    if structured:
        from .native_structure import structure_package
        write(out/'native-structure.json',structure_package(out/'normalized.pptx',out/'candidate.pptx',spec))
    package=check_package(out/'candidate.pptx');native=inspect_native(out/'candidate.pptx',spec)
    for name,result in [('package',package),('native',native),('ledger',ledger)]:
        details={k:result.details.get(k) for k in ('part_count','slide_parts')} if name=='package' else result.details
        write(out/(name+'-check.json'),dict(status=result.status,issues=result.issues,unknown=result.unknown,evaluated=result.evaluated,details=details))
    if any(i['severity']=='error' for i in package.issues) or native.status!='passed':raise ValueError('Normalized editorial output failed package/native checks; see diagnostics')
    result=dict(status='built',deck=str(out/'candidate.pptx'),spec=str(source),raw=str(out/'raw.pptx'),
        normalization_log=str(out/'normalization.json'),normalization_edits=len(normalization['edits']),
        native_status=native.status,package_status=package.status,visual_review='required in actual target application',release_allowed=False)
    write(out/'build.json',result);return result
