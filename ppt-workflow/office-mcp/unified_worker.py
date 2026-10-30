"""Create the frozen native template first, then apply it to owned scene content."""
import gc
import json
import subprocess
import sys
from pathlib import Path
import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[1]
req,report=map(Path,sys.argv[1:3]);q=json.loads(req.read_text(encoding="utf-8"))
profile=json.loads(Path(q["design_system"]).read_text(encoding="utf-8"))
record=dict(status="failed",error=None,operations=[]);app=None;pres=None;owned=False


def rgb(s):return int(s[:2],16)+256*int(s[2:4],16)+65536*int(s[4:],16)


def text_style(shape,size,color,bold=False):
    tf=shape.TextFrame;tf.MarginLeft=0;tf.MarginRight=0;tf.MarginTop=0;tf.MarginBottom=0
    tf.TextRange.Font.Name=profile["font"];tf.TextRange.Font.Size=size;tf.TextRange.Font.Color.RGB=rgb(color);tf.TextRange.Font.Bold=bold


def build_template():
    global pres
    pres=app.Presentations.Add(False);pres.PageSetup.SlideWidth=profile["canvas"]["width"]*72;pres.PageSetup.SlideHeight=540
    pres.SlideMaster.ApplyTheme(str(Path("C:/Program Files/Microsoft Office/root/Document Themes 16/Office Theme.thmx")))
    c=profile["colors"]
    for i,color in enumerate([c["ink"],"FFFFFF",c["ink"],c["background"],c["accent"],c["soft"],c["muted"],c["rule"],c["accent"],c["muted"],c["accent"],c["muted"]],1):pres.SlideMaster.Theme.ThemeColorScheme.Colors(i).RGB=rgb(color)
    for i,item in enumerate(profile["layouts"],1):
        layout=pres.SlideMaster.CustomLayouts.Add(pres.SlideMaster.CustomLayouts.Count+1);layout.Name=item["name"]
        for j in range(layout.Shapes.Count,0,-1):layout.Shapes.Item(j).Delete()
        layout.FollowMasterBackground=False;layout.DisplayMasterShapes=False;layout.Background.Fill.Solid();layout.Background.Fill.ForeColor.RGB=rgb(c["background"])
        shape=layout.Shapes.AddPlaceholder(1,*[v*72 for v in profile["regions"]["title"]]);shape.Name="Unified title";text_style(shape,34,c["ink"],True)
        for slot in item["slots"]:
            shape=layout.Shapes.AddPlaceholder(18 if slot["kind"]=="picture" else 2,*[v*72 for v in slot["rect"]])
            shape.Name=slot["name"];text_style(shape,22,c["ink"])
        slide=pres.Slides.AddSlide(i,layout)
        slide.Shapes.Title.TextFrame.TextRange.Text=item["name"].split(" ",2)[2]+" 布局"
        for j in range(2,slide.Shapes.Placeholders.Count+1):
            ph=slide.Shapes.Placeholders(j)
            if ph.PlaceholderFormat.Type!=18:ph.TextFrame.TextRange.Text="替换此处内容"
    wanted={x["name"] for x in profile["layouts"]}
    for j in range(pres.SlideMaster.CustomLayouts.Count,0,-1):
        if pres.SlideMaster.CustomLayouts.Item(j).Name not in wanted:pres.SlideMaster.CustomLayouts.Item(j).Delete()
    pres.SaveAs(q["template"],26);pres.SaveCopyAs(q["preview"],24)
    record.update(status="completed",layout_names=[x["name"] for x in profile["layouts"]],slide_count=10)
    record["operations"].append(dict(kind="template-first",profile_id=profile["id"],template=q["template"]))


def apply_template():
    global pres
    spec=json.loads(Path(q["spec"]).read_text(encoding="utf-8"));c=profile["colors"]
    pres=app.Presentations.Open(q["input"],False,False,False)
    pres.ApplyTemplate(q["template_source"])
    layouts={l.Name:l for master in pres.Designs for l in master.SlideMaster.CustomLayouts}
    lookup={x["key"]:x["name"] for x in profile["layouts"]}
    for i,page in enumerate(spec["slides"],1):
        slide=pres.Slides.Item(i);slide.CustomLayout=layouts[lookup[page["layout"]]];slide.DisplayMasterShapes=False
        slide.FollowMasterBackground=False;slide.Background.Fill.Solid();slide.Background.Fill.ForeColor.RGB=rgb(c["background"])
        for j in range(slide.Shapes.Count,0,-1):
            if slide.Shapes.Item(j).Type==14:slide.Shapes.Item(j).Delete()
        for e in page["elements"]:
            if e["type"]=="chart" and spec.get('schema_version')!='0.2':
                ch=slide.Shapes.Item(e["id"]).Chart;ch.ChartStyle=10
                for point,col in [(1,"9AB1B3"),(2,c["accent"])]:ch.SeriesCollection(1).Points(point).Format.Fill.ForeColor.RGB=rgb(col)
            if e["type"]=="diagram":
                slide.Shapes.Item(e["id"]).Delete();r=e["rect"];step=r["w"]/len(e["diagram"]["nodes"]);names=[]
                for k,label in enumerate(e["diagram"]["nodes"]):
                    sh=slide.Shapes.AddShape(52,(r["x"]+k*step)*72,r["y"]*72,(step-.06)*72,r["h"]*72)
                    sh.Name=e["id"]+f"-node-{k+1}";names.append(sh.Name);sh.Fill.ForeColor.RGB=rgb(c["accent"]);sh.Line.Visible=False
                    sh.TextFrame.TextRange.Text=label;text_style(sh,22,"FFFFFF")
                    sh.TextFrame.TextRange.ParagraphFormat.Alignment=2;sh.TextFrame.VerticalAnchor=3;sh.TextFrame.WordWrap=False
                group=slide.Shapes.Range(names).Group();group.Name=e["id"]
    used={pres.Slides.Item(i).Design.Name for i in range(1,pres.Slides.Count+1)}
    for j in range(pres.Designs.Count,0,-1):
        if pres.Designs.Item(j).Name not in used:pres.Designs.Item(j).Delete()
    pres.SaveAs(q["output"],24);pres.SaveCopyAs(q["template"],26)
    record.update(status="completed",slide_count=pres.Slides.Count,slide_layouts=[dict(slide=i,name=pres.Slides.Item(i).CustomLayout.Name) for i in range(1,pres.Slides.Count+1)])
    record["operations"].append(dict(kind="apply-frozen-template",source=q["template_source"],profile_id=profile["id"]))


pythoncom.CoInitialize()
try:
    p=subprocess.run(["powershell","-NoProfile","-Command","@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode or p.stdout.strip()!="0":raise RuntimeError("Existing user PowerPoint session or uncertain state; refused")
    app=win32com.client.DispatchEx("PowerPoint.Application");owned=app.Presentations.Count==0
    if not owned:raise RuntimeError("Existing presentations; refused")
    record.update(version=app.Version,build=app.Build)
    if q["operation"]=="unified-template":build_template()
    elif q["operation"]=="enhance":apply_template()
    else:raise ValueError("Unsupported unified operation")
except Exception as exc:record.update(status="failed",error=f"{type(exc).__name__}: {exc}")
finally:
    if pres is not None:
        try:pres.Close()
        except Exception as exc:record["cleanupError"]=str(exc)
    pres=None
    if app is not None and owned:
        try:
            if app.Presentations.Count==0:app.Quit()
            else:record["cleanupError"]="Unexpected other presentation retained"
        except Exception as exc:record["cleanupError"]=str(exc)
    app=None;gc.collect();pythoncom.CoUninitialize();record["cleanupCompleted"]="cleanupError" not in record
    report.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
raise SystemExit(0 if record["status"]=="completed" and record["cleanupCompleted"] else 1)
