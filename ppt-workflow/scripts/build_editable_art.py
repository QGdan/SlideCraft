"""Rebuild semantic report/lens components as native shapes plus editable SVG.

This is a user-requested editable approximation, not lossless PNG vectorization.
"""
import json
import sys
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from ppt_workflow.render import save,powerpoint_lock,sha256


def node(kind,name,**kw):return dict(kind=kind,id=name,**kw)


NODES=[
 node("rect","back-paper",x=27,y=8,w=235,h=310,fill="EBEFEB",stroke="CEDCD8",weight=1),
 node("rect","report-sheet",x=18,y=18,w=235,h=310,fill="FFFFFF",stroke="CEDCD8",weight=1),
 node("rect","report-heading",x=39,y=40,w=192,h=43,fill="117A7E",stroke="117A7E",weight=0),
 node("text","report-title",x=47,y=44,w=176,h=35,text="汇总结果",size=28,color="FFFFFF"),
 *[node("rect",f"text-line-{i}",x=42,y=110+i*37,w=176 if i%2==0 else 144,h=9,fill="CEDCD8",stroke="CEDCD8",weight=0) for i in range(5)],
 node("line","lens-handle",x=295,y=244,w=83,h=84,color="162E3B",weight=15),
 node("ellipse","review-lens",x=171,y=99,w=181,h=181,fill="E2EFEB",stroke="117A7E",weight=6,opacity=.82),
 node("text","review-label",x=208,y=149,w=106,h=75,text="教师\n审核",size=28,color="117A7E")]


def svg(nodes):
    import html
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">','<title>报告与教师审核：可编辑语义重建</title>']
    for n in nodes:
        common=f'id="{n["id"]}"'
        if n["kind"]=="rect":parts.append(f'<rect {common} x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" fill="#{n["fill"]}" stroke="#{n["stroke"]}" stroke-width="{n["weight"]}"/>')
        elif n["kind"]=="ellipse":parts.append(f'<ellipse {common} cx="{n["x"]+n["w"]/2}" cy="{n["y"]+n["h"]/2}" rx="{n["w"]/2}" ry="{n["h"]/2}" fill="#{n["fill"]}" fill-opacity="{n["opacity"]}" stroke="#{n["stroke"]}" stroke-width="{n["weight"]}"/>')
        elif n["kind"]=="line":parts.append(f'<line {common} x1="{n["x"]}" y1="{n["y"]}" x2="{n["x"]+n["w"]}" y2="{n["y"]+n["h"]}" stroke="#{n["color"]}" stroke-width="{n["weight"]}"/>')
        elif n["kind"]=="text":
            lines=n["text"].split("\n");base=n["y"]+n["h"]/2-(len(lines)-1)*n["size"]*.55
            parts.append(f'<text {common} x="{n["x"]+n["w"]/2}" y="{base}" fill="#{n["color"]}" font-family="Microsoft YaHei,sans-serif" font-size="{n["size"]}" text-anchor="middle" dominant-baseline="middle">'+''.join(f'<tspan x="{n["x"]+n["w"]/2}" dy="{0 if i==0 else n["size"]*1.1}">{html.escape(s)}</tspan>' for i,s in enumerate(lines))+'</text>')
    return "\n".join(parts+['</svg>'])


if __name__=="__main__":
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
    save(out/"editable-nodes.json",NODES);(out/"report-review-editable.svg").write_text(svg(NODES),encoding="utf-8")
    with powerpoint_lock(ROOT/"runs/.powerpoint-worker-lock") as lock:
        try:
            run=subprocess.run([str(ROOT/".mcp-venv/Scripts/python.exe"),str(ROOT/"office-mcp/editable_art_worker.py"),str(out)],capture_output=True,text=True,encoding="utf-8",timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
            (out/"worker.log").write_text(run.stdout+run.stderr,encoding="utf-8")
            if run.returncode:raise RuntimeError(run.stderr)
        except Exception:
            if not (out/"worker.json").exists():save(lock/"quarantine.json",dict(reason="Editable-art worker missing cleanup evidence",report=str(out)))
            raise
    print("Editable native shapes and SVG saved",flush=True)
