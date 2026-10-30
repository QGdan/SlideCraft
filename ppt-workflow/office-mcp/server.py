"""Project-local MCP server. Run with isolated .mcp-venv; no arbitrary evaluation tool."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from mcp.server import MCPServer
from ppt_workflow.office_bridge import native_operation

server=MCPServer("ppt-workflow-office")


@server.tool()
def create_wps_template_copy(request_path:str,output_dir:str)->dict:
    """Create an independent local WPS PPTX/POTX template copy, apply expected-text-checked shape-ID edits, retain selected pages, save/reopen and export PNG. Never quits WPS or edits source/user documents. Request JSON and fresh output must be project-local."""
    from ppt_workflow.wps_bridge import create_template_copy
    return create_template_copy(request_path,output_dir)


@server.tool()
def probe_wps_connection(output_dir:str)->dict:
    """Query desktop WPS version and presentation count via COM, allowing background sessions. Never opens, saves, closes documents or quits WPS. Does not certify template editing/rendering or WPS cloud API access."""
    import json
    import subprocess
    from ppt_workflow.office_bridge import workspace_path
    out=workspace_path(output_dir)
    if not out.is_relative_to(ROOT/"runs") or out==ROOT/"runs":
        raise ValueError("Fresh output subdirectory inside runs required")
    if out.exists():raise ValueError("Fresh output required")
    proc=subprocess.run([sys.executable,str(ROOT/"scripts/probe_wps.py"),str(out),"--allow-existing-readonly"],
                        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=55)
    report=out/"wps-worker.json"
    if not report.is_file():raise RuntimeError("WPS probe incomplete: "+proc.stdout+proc.stderr)
    result=json.loads(report.read_text(encoding="utf-8"))
    if proc.returncode or result.get("status")!="connected":raise RuntimeError(result)
    return {"transport":"MCP stdio -> local desktop WPS COM","report":str(report),**result}


@server.tool()
def inspect_template_resources(template_path:str,output_dir:str)->dict:
    """Inventory a local POTX/PPTX's masters, layouts, editable object IDs, theme fonts/colors and media. Read-only input; no Office launch. Does not certify visual quality or compose compatibility."""
    from ppt_workflow.template_resources import inspect_template
    return inspect_template(template_path,output_dir)


@server.tool()
def health_check()->dict:
    """Inspect local dependencies and registry without opening Office. COM availability requires a real worker operation."""
    from ppt_workflow.workflow import doctor
    return {"server":"ppt-workflow-office","transport":"stdio","project_root":str(ROOT),"diagnostics":doctor()}


@server.tool()
def create_unified_template(output_dir:str)->dict:
    """Create a native POTX with the frozen ivory/teal design system and ten named layouts before adding real content."""
    return native_operation("unified-template",output_dir)


@server.tool()
def catalog_native_features(output_dir:str)->dict:
    """List native SmartArt layouts, styles and installed themes in a fresh report directory. Refuses existing PowerPoint sessions."""
    return native_operation("catalog",output_dir)


@server.tool()
def apply_editorial_design(sample_dir:str,output_dir:str)->dict:
    """Apply native themes/layouts/chart styling and editable grouped flow shapes to a fresh PPTX/POTX. Unified inputs use their frozen template. SmartArt is conditional, not guaranteed. Paths must stay in this project."""
    return native_operation("enhance",output_dir,sample=sample_dir)


@server.tool()
def create_from_template(template_path:str,output_dir:str)->dict:
    """Create a fresh PowerPoint presentation from a local POTX using Office's Untitled copy semantics. Does not overwrite the template."""
    return native_operation("instantiate",output_dir,template=template_path)


if __name__=="__main__":server.run(transport="stdio")
