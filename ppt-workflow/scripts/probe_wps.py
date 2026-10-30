"""Bounded WPS COM probe; optional explicitly authorized read-only shared-session check."""
import argparse
import gc
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def readonly_worker(report):
    """Inspect application metadata only. Never quit, close, open or save documents."""
    import pythoncom
    import win32com.client
    app = None
    result = dict(status="unverified", mode="shared-session-readonly", cleanupCompleted=False,
                  application_quit_called=False, document_mutations=False)
    pythoncom.CoInitialize()
    try:
        try:
            app = win32com.client.GetActiveObject("KWPP.Application")
            result["activation"] = "existing-active-object"
        except pythoncom.com_error as exc:
            result["active_object_error"] = str(exc)
            app = win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}",
                clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)
            result["activation"] = "32-bit-local-server-no-quit"
        # Do not inspect titles or contents of the user's open files.
        result.update(status="connected", version=str(app.Version),
                      presentation_count=int(app.Presentations.Count),
                      scope="Application metadata only; template editing/save/render and online template library not verified")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        app = None
        gc.collect()
        pythoncom.CoUninitialize()
        result["cleanupCompleted"] = True  # references released; WPS deliberately remains running
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["status"] == "connected" else 1


def worker(report, allow_existing=False):
    if allow_existing:
        return readonly_worker(report)
    import pythoncom
    import win32com.client
    result = dict(status="unverified", cleanupCompleted=False, progid="KWPP.Application")
    app = None
    owned = False
    pythoncom.CoInitialize()
    try:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            "@(Get-Process -Name wps,wpp -ErrorAction SilentlyContinue).Count"],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        result["process_check"] = dict(returncode=probe.returncode, count=probe.stdout.strip(), stderr=probe.stderr)
        if probe.returncode or probe.stdout.strip() != "0":
            raise RuntimeError("Existing WPS process or uncertain process state; refused")
        # Installed WPS registers its out-of-process server in the 32-bit view.
        app = win32com.client.DispatchEx("{44720441-94BF-4940-926D-4F38FECF2A48}",
            clsctx=pythoncom.CLSCTX_LOCAL_SERVER | 0x40000)
        owned = app.Presentations.Count == 0
        if not owned:
            raise RuntimeError("WPS has presentations; no document access attempted")
        result.update(status="connected", version=str(app.Version), presentation_count=0,
                      scope="COM handshake only; template/save/render not verified")
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}")
    finally:
        if app is not None and owned:
            try:
                if app.Presentations.Count == 0:
                    app.Quit()
                else:
                    raise RuntimeError("Unexpected presentation; WPS retained")
            except Exception as exc:
                result["cleanupError"] = str(exc)
        app = None
        gc.collect()
        pythoncom.CoUninitialize()
        result["cleanupCompleted"] = "cleanupError" not in result
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["status"] == "connected" and result["cleanupCompleted"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-existing-readonly", action="store_true",
                        help="Query WPS application metadata even with background processes; never quit WPS")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "runs"):
        parser.error("Output must stay inside project runs")
    if args.worker:
        return worker(output, args.allow_existing_readonly)
    output.mkdir(parents=True, exist_ok=False)
    import winreg
    registration = []
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        key = r"CLSID\{44720441-94BF-4940-926D-4F38FECF2A48}\LocalServer32"
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key, 0, winreg.KEY_READ | view) as handle:
                registration.append(dict(view=view, server=winreg.QueryValue(handle, None)))
        except OSError:
            pass
    (output / "registration.json").write_text(json.dumps(registration, ensure_ascii=False, indent=2), encoding="utf-8")
    from ppt_workflow.render import powerpoint_lock
    with powerpoint_lock(ROOT / "runs/.powerpoint-worker-lock") as lock:
        try:
            command = [sys.executable, str(Path(__file__).resolve()), str(output / "wps-worker.json"), "--worker"]
            if args.allow_existing_readonly:
                command.append("--allow-existing-readonly")
            proc = subprocess.run(command,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            result = json.loads((output / "wps-worker.json").read_text(encoding="utf-8"))
            if not result["cleanupCompleted"]:
                (lock / "quarantine.json").write_text(json.dumps(result), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False))
            return proc.returncode
        except subprocess.TimeoutExpired:
            result = dict(status="unverified", reason="WPS COM timeout; no global process termination attempted")
            (lock / "quarantine.json").write_text(json.dumps(result), encoding="utf-8")
            (output / "timeout.json").write_text(json.dumps(result), encoding="utf-8")
            print(json.dumps(result))
            return 2


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
