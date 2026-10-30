"""Fresh outputs, bounded subprocesses and explicit renderer verification."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from PIL import Image
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


class WorkerBusy(RuntimeError):
    pass


@contextmanager
def powerpoint_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        path.mkdir(exist_ok=False)
    except FileExistsError:
        raise WorkerBusy("PowerPoint worker is busy or quarantined; existing lock retained")
    save(path/"owner.json",{"pid":os.getpid(),"started_at":datetime.now(timezone(timedelta(hours=8))).isoformat()})
    try:
        yield path
    finally:
        if not (path/"quarantine.json").exists():
            (path/"owner.json").unlink()
            path.rmdir()


def verify_images(directory,expected,width,height):
    files = sorted(Path(directory).glob("slide-*.png"),key=lambda p:int(re.search(r"(\d+)\.png$",p.name).group(1)) if re.search(r"(\d+)\.png$",p.name) else -1)
    if len(files)!=expected:
        raise ValueError(f"Expected {expected} PNG files, got {len(files)}")
    pages = []
    records = []
    for path in files:
        match = re.fullmatch(r"slide-(\d+)\.png",path.name)
        if not match:
            raise ValueError("Unexpected PNG name")
        page = int(match.group(1))
        pages.append(page)
        with Image.open(path) as image:
            image.load()
            if image.format!="PNG" or image.size!=(width,height):
                raise ValueError(f"Unexpected image format/dimensions: {path.name}")
        records.append({"slide":page,"path":str(path.resolve()),"sha256":sha256(path),"size_px":[width,height]})
    if pages!=list(range(1,expected+1)):
        raise ValueError("PNG page indices are duplicated, missing or unordered")
    return records


def render_deck(path,out,*,renderer="powerpoint",width=1600,height=900,timeout=60,
                lock_path=None,runner=subprocess.run,find_tool=shutil.which):
    path,out = Path(path).resolve(),Path(out).resolve()
    report = {"status":"unverified","renderer":renderer,"input_path":str(path),
              "created_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),
              "width":width,"height":height,"timeout_seconds":timeout,"commands":[],"images":[],"error":None}
    if out.exists():
        report["status"]="failed"; report["error"]="Output directory already exists; stale files were not inspected or overwritten"
        return report
    out.mkdir(parents=True,exist_ok=False)
    start = time.perf_counter()

    def run(command):
        remaining = timeout-(time.perf_counter()-start)
        if remaining<=0:
            raise subprocess.TimeoutExpired(command,timeout)
        kwargs = {"capture_output":True,"text":True,"encoding":"utf-8","errors":"replace","timeout":remaining}
        if os.name=="nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        completed = runner(command,**kwargs)
        report["commands"].append({"command":list(map(str,command)),"returncode":completed.returncode,"stdout":completed.stdout,"stderr":completed.stderr})
        if completed.returncode!=0:
            raise RuntimeError(f"Renderer command failed with exit {completed.returncode}")
        return completed

    try:
        if width<=0 or height<=0 or timeout<=0:
            raise ValueError("Dimensions and timeout must be positive")
        report["input_sha256"] = sha256(path)
        count = len(Presentation(path).slides)
        if count==0:
            raise ValueError("Empty deck")
        report["expected_slide_count"] = count
        slide_dir = out/"slides"
        if renderer=="powerpoint":
            shell = find_tool("powershell")
            if not shell:
                raise FileNotFoundError("PowerShell not found")
            lock_path = lock_path or ROOT/"runs/.powerpoint-worker-lock"
            with powerpoint_lock(lock_path) as lock:
                try:
                    worker_report = out/"powerpoint-worker.json"
                    run([shell,"-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"render/windows.ps1"),
                         "-Pptx",str(path),"-OutDir",str(slide_dir),"-Report",str(worker_report),"-Width",str(width),"-Height",str(height)])
                    if not worker_report.is_file():
                        raise ValueError("COM worker returned no evidence report")
                    worker = json.loads(worker_report.read_text(encoding="utf-8-sig"))
                    report["worker"] = worker
                    if worker.get("cleanupCompleted") is not True or worker.get("cleanupError"):
                        save(lock/"quarantine.json",{"reason":"cleanup failed","report":str(out)})
                        raise ValueError("COM cleanup failed; worker quarantined")
                    if worker.get("status")!="exported" or worker.get("inputSha256")!=report["input_sha256"] or worker.get("slideCount")!=count:
                        raise ValueError("COM worker evidence does not match the requested input")
                except subprocess.TimeoutExpired:
                    save(lock/"quarantine.json",{"reason":"timeout; COM ownership unknown","report":str(out)})
                    raise
                except Exception:
                    if worker_report.is_file():
                        try:
                            report["worker"] = json.loads(worker_report.read_text(encoding="utf-8-sig"))
                        except (OSError,ValueError):
                            report["worker"] = {}
                        if report["worker"].get("cleanupCompleted") is not True or report["worker"].get("cleanupError"):
                            save(lock/"quarantine.json",{"reason":"cleanup failed","report":str(out)})
                    else:
                        save(lock/"quarantine.json",{"reason":"worker exit without cleanup evidence","report":str(out)})
                    raise
        elif renderer=="libreoffice":
            soffice = find_tool("soffice") or find_tool("libreoffice")
            pdftoppm = find_tool("pdftoppm")
            if not soffice or not pdftoppm:
                raise FileNotFoundError("LibreOffice and pdftoppm are both required for PNG export")
            slide_dir.mkdir()
            profile = out/"lo-profile"
            run([soffice,"--headless","--norestore","--nologo",f"-env:UserInstallation={profile.as_uri()}","--convert-to","pdf","--outdir",str(out),str(path)])
            pdf = out/(path.stem+".pdf")
            if not pdf.is_file() or pdf.stat().st_size==0:
                raise ValueError("LibreOffice produced no PDF")
            report["pdf_sha256"] = sha256(pdf)
            run([pdftoppm,"-png","-scale-to-x",str(width),"-scale-to-y",str(height),str(pdf),str(slide_dir/"slide")])
        else:
            raise ValueError("Unknown renderer")
        report["images"] = verify_images(slide_dir,count,width,height)
        if sha256(path)!=report["input_sha256"]:
            raise ValueError("Input changed while rendering")
        report["status"]="passed"
    except WorkerBusy as exc:
        report["status"]="needs_review"; report["error"]=str(exc)
    except subprocess.TimeoutExpired:
        report["status"]="unverified"; report["error"]="Renderer timed out; only this invocation's helper was terminated; no global PowerPoint kill"
    except Exception as exc:
        report["status"]="failed"; report["error"]=f"{type(exc).__name__}: {exc}"
    report["elapsed_seconds"] = round(time.perf_counter()-start,3)
    save(out/"render-manifest.json",report)
    return report
