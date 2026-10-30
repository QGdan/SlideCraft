import gc
import json
import sys
import subprocess
from pathlib import Path
import pythoncom
import win32com.client
out=Path(sys.argv[1]);nodes=json.loads((out/"editable-nodes.json").read_text(encoding="utf-8"));app=None;pres=None;owned=False
r=dict(status="failed",error=None,cleanupCompleted=False)
def rgb(s):return int(s[:2],16)+256*int(s[2:4],16)+65536*int(s[4:],16)
def text(slide,label,x,y,w,h,size,color):
    sh=slide.Shapes.AddTextbox(1,x*72,y*72,w*72,h*72);sh.TextFrame.TextRange.Text=label
    sh.TextFrame.TextRange.Font.Name="Microsoft YaHei";sh.TextFrame.TextRange.Font.Size=size;sh.TextFrame.TextRange.Font.Color.RGB=rgb(color)
    sh.TextFrame.TextRange.Font.Bold=size in (12,34)
    sh.TextFrame.MarginLeft=0;sh.TextFrame.MarginRight=0;sh.TextFrame.MarginTop=0;sh.TextFrame.MarginBottom=0
    return sh
pythoncom.CoInitialize()
try:
    probe=subprocess.run(["powershell","-NoProfile","-Command","@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    if probe.returncode or probe.stdout.strip()!="0":raise RuntimeError("Existing PowerPoint session; refused")
    app=win32com.client.DispatchEx("PowerPoint.Application");owned=app.Presentations.Count==0
    if not owned:raise RuntimeError("Existing presentations; refused")
    pres=app.Presentations.Add(False);pres.PageSetup.SlideWidth=960;pres.PageSetup.SlideHeight=540
    sl=pres.Slides.Add(1,12);sl.FollowMasterBackground=False;sl.Background.Fill.Solid();sl.Background.Fill.ForeColor.RGB=rgb("F5F3ED")
    text(sl,"可编辑图形模块",.7,.93,11.9,.87,34,"162E3B")
    text(sl,"报告与教师审核",.7,.36,11.9,.28,12,"117A7E")
    names=[]
    for n in nodes:
        x=.85+n["x"]*.013;y=2.02+n["y"]*.013;w=n["w"]*.013;h=n["h"]*.013
        if n["kind"]=="text":
            sh=text(sl,n["text"],x,y,w,h,n["size"]*.013*72,n["color"]);sh.TextFrame.VerticalAnchor=3;sh.TextFrame.TextRange.ParagraphFormat.Alignment=2
        elif n["kind"]=="line":
            sh=sl.Shapes.AddLine(x*72,y*72,(x+w)*72,(y+h)*72);sh.Line.ForeColor.RGB=rgb(n["color"]);sh.Line.Weight=n["weight"]*.013*72
        else:
            sh=sl.Shapes.AddShape(9 if n["kind"]=="ellipse" else 1,x*72,y*72,w*72,h*72)
            sh.Fill.ForeColor.RGB=rgb(n["fill"]);sh.Fill.Transparency=1-n.get("opacity",1)
            sh.Line.ForeColor.RGB=rgb(n["stroke"]);sh.Line.Weight=n["weight"]*.013*72
            if not n["weight"]:sh.Line.Visible=False
        sh.Name=n["id"];names.append(n["id"])
    group=sl.Shapes.Range(names).Group();group.Name="Editable report review"
    text(sl,"文字、颜色与尺寸可单独修改\n组合可以取消组合后继续编辑\nSVG 可作为 Figma 导入素材",7.2,2.7,5.15,2.6,22,"536876")
    text(sl,"根据概念图语义重建，非原图分层或无损矢量化。",.7,7.02,11.6,.27,11,"536876")
    group=None;sh=None;sl=None;pres.SaveAs(str(out/"editable-components.pptx"),24);pres.Close();pres=None
    pres=app.Presentations.Open(str(out/"editable-components.pptx"),True,False,False)
    group=pres.Slides.Item(1).Shapes.Item("Editable report review")
    actual=[dict(name=group.GroupItems.Item(i).Name,type=group.GroupItems.Item(i).Type) for i in range(1,group.GroupItems.Count+1)]
    if len(actual)!=len(nodes) or any(s["type"]==13 for s in actual):raise ValueError("Native components lost after reopen")
    r.update(status="passed",native_children=actual,raster_children=0,svg="report-review-editable.svg");group=None
except Exception as exc:r["error"]=str(exc)
finally:
    if pres is not None:
        try:pres.Close()
        except Exception as exc:r["cleanupError"]=str(exc)
    pres=None
    if app is not None and owned:
        try:
            if app.Presentations.Count==0:app.Quit()
        except Exception as exc:r["cleanupError"]=str(exc)
    app=None;gc.collect();pythoncom.CoUninitialize();r["cleanupCompleted"]="cleanupError" not in r
    (out/"worker.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
raise SystemExit(0 if r["status"]=="passed" and r["cleanupCompleted"] else 1)
