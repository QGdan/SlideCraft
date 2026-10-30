"""Update only this runtime's installed skill copies, after saving their exact previous files."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import argparse,json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--dest',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
record=a.record.resolve()
if not record.is_relative_to(ROOT.parent):raise ValueError('Save update evidence inside this project')
names=['ppt-quality-workflow']+[s['skill'] for s in json.loads((ROOT/'skill-routing.json').read_text(encoding='utf-8'))['stages']]
targets=[(ROOT/'skills'/n,a.dest.resolve()/n) for n in names]
for source,target in targets:
    binding=json.loads((target/'runtime.json').read_text(encoding='utf-8'))
    if Path(binding['project_root']).resolve()!=ROOT:raise ValueError('Refused to update a skill bound to a different runtime')
    if not (source/'SKILL.md').is_file():raise ValueError('Missing source skill')
record.parent.mkdir(parents=True,exist_ok=True)
backup=record.parent/'installed-skills-before-20261017.zip'
if a.apply:
    if backup.exists():raise ValueError('Previous backup already exists; use a new record directory')
    with ZipFile(backup,'w',ZIP_DEFLATED) as z:
        for _,target in targets:
            for file in target.rglob('*'):
                if file.is_file():z.write(file,Path(target.name)/file.relative_to(target))
    for source,target in targets:
        for file in source.rglob('*'):
            if not file.is_file() or file.name=='runtime.json':continue
            output=target/file.relative_to(source);output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,output)
    checks=[]
    for source,target in targets:
        equal=all(hashlib.sha256(file.read_bytes()).hexdigest()==hashlib.sha256((target/file.relative_to(source)).read_bytes()).hexdigest()
            for file in source.rglob('*') if file.is_file() and file.name!='runtime.json')
        checks.append({'skill':source.name,'source_matches':equal,'runtime':json.loads((target/'runtime.json').read_text(encoding='utf-8'))})
    if not all(r['source_matches'] for r in checks):raise RuntimeError('Skill copy verification failed')
else:checks=[{'skill':s.name,'destination':str(t)} for s,t in targets]
result={'status':'updated-and-verified' if a.apply else 'preview','skills':checks,'backup':str(backup) if a.apply else None,
    'other_skills_changed':False,'global_configuration_changed':False}
record.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':result['status'],'skills':len(checks)},ensure_ascii=False))
