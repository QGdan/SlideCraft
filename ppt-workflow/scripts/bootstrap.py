"""Install the Windows candidate into fresh local environments from verified wheels."""
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--node',type=Path,required=True)
    p.add_argument('--npm-cli',type=Path)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();node=a.node.resolve();npm=(a.npm_cli or node.parent/'node_modules/npm/bin/npm-cli.js').resolve()
    if os.name!='nt' or sys.version_info[:2]!=(3,12) or platform.machine().lower() not in ('amd64','x86_64'):
        raise SystemExit('This verified bundle requires Windows x64 and Python 3.12; other platforms are untested')
    if not node.is_file() or not npm.is_file():raise SystemExit('Explicit Node and npm-cli.js executables are required')
    targets=[ROOT/'.venv',ROOT/'.mcp-venv',ROOT/'node_modules']
    if any(p.exists() for p in targets):raise SystemExit('Existing environment detected; extract to a fresh directory. Nothing replaced.')
    manifest=json.loads((ROOT/'vendor/manifest.json').read_text(encoding='utf-8'))
    for r in manifest:
        f=ROOT/r['path']
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=r['sha256']:
            raise SystemExit('Dependency hash mismatch: '+r['path'])
    if not a.apply:
        print(json.dumps({'status':'preview','root':str(ROOT),'targets':list(map(str,targets)),'network_required':False}));return
    log={'status':'running','commands':[],'python':sys.version,'node':str(node),'offline':True};started=time.perf_counter()
    dest=ROOT/'installation.json'
    temporary=ROOT/'.tmp';temporary.mkdir(exist_ok=True)
    environment={**os.environ,'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'PYTHONUTF8':'1'}
    def run(argv,timeout=180):
        proc=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',
            timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW,env=environment)
        log['commands'].append({'command':list(map(str,argv)),'exit':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
        dest.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        if proc.returncode:raise RuntimeError('Installation command failed; see installation.json')
    try:
        run([node,'--version'])
        for name,lock in [('.venv','runtime'),('.mcp-venv','office')]:
            run([sys.executable,'-m','venv',ROOT/name])
            py=ROOT/name/'Scripts/python.exe'
            run([py,'-m','pip','install','--disable-pip-version-check','--no-index','--find-links',ROOT/'vendor/wheels',
                 '--require-hashes','--report',ROOT/f'{lock}-install-report.json','-r',ROOT/f'vendor/{lock}.lock.txt'])
            run([py,'-m','pip','check'])
        for tarball in sorted((ROOT/'vendor/npm-tarballs').glob('*.tgz')):
            run([node,npm,'cache','add',tarball,'--offline','--ignore-scripts','--cache',ROOT/'.npm'])
        run([node,npm,'ci','--offline','--ignore-scripts','--no-audit','--no-fund','--cache',ROOT/'.npm'])
        (ROOT/'runs').mkdir(exist_ok=True)
        log['status']='installed'
    except Exception as exc:
        log.update(status='failed',error=str(exc));raise
    finally:
        log['seconds']=round(time.perf_counter()-started,3)
        dest.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':log['status'],'seconds':log['seconds'],'report':str(dest)}))
if __name__=='__main__':main()
