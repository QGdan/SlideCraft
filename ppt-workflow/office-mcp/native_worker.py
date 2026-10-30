"""Disposable, owned Office COM worker. No takeover of an existing PowerPoint session."""
import gc
import json
import subprocess
import sys
from pathlib import Path
import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[1]
request_path,report_path=map(Path,sys.argv[1:3])
q=json.loads(request_path.read_text(encoding="utf-8"))
record=dict(status="failed",operations=[],error=None,cleanupCompleted=False)
app=None;pres=None;owned=False


def rgb(color):
    return int(color[0:2],16)+256*int(color[2:4],16)+65536*int(color[4:6],16)


def placeholder(layout,kind,rect,name,size,color):
    shape=layout.Shapes.AddPlaceholder(kind,*[v*72 for v in rect])
    shape.Name=name
    shape.TextFrame.TextRange.Font.Name="Microsoft YaHei"
    shape.TextFrame.TextRange.Font.Size=size
    shape.TextFrame.TextRange.Font.Color.RGB=rgb(color)
    return shape


pythoncom.CoInitialize()
try:
    probe=subprocess.run(["powershell","-NoProfile","-Command","@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    if probe.returncode or probe.stdout.strip()!="0":raise RuntimeError("Existing PowerPoint session or uncertain process state; refused")
    app=win32com.client.DispatchEx("PowerPoint.Application")
    owned=app.Presentations.Count==0
    if not owned:raise RuntimeError("PowerPoint has presentations; refused")
    record.update(version=app.Version,build=app.Build)
    if q["operation"]=="catalog":pres=app.Presentations.Add(False)
    elif q["operation"]=="enhance":pres=app.Presentations.Open(str(Path(q["input"]).resolve()),False,False,False)
    elif q["operation"]=="instantiate":pres=app.Presentations.Open(str(Path(q["input"]).resolve()),False,True,False)
    try:
        layouts=[dict(id=app.SmartArtLayouts.Item(i).Id,name=app.SmartArtLayouts.Item(i).Name) for i in range(1,app.SmartArtLayouts.Count+1)]
        record["smartart_supported"]=True
    except Exception as exc:
        layouts=[];record.update(smartart_supported=False,smartart_error=str(exc))
    if q["operation"]=="catalog":
        record.update(status="completed",smartart_layouts=layouts,
                      installed_themes=[str(p) for p in Path("C:/Program Files/Microsoft Office/root/Document Themes 16").glob("*.thmx")])
    elif q["operation"]=="instantiate":
        if Path(q["output"]).exists():raise RuntimeError("Fresh template instance output required")
        pres.SaveAs(q["output"],24)
        record.update(status="completed",slide_count=pres.Slides.Count,layouts=[pres.Slides.Item(i).CustomLayout.Name for i in range(1,pres.Slides.Count+1)],
                      operations=[dict(kind="native-template-new-presentation",untitled_copy=True)])
    elif q["operation"]=="enhance":
        spec=json.loads(Path(q["spec"]).read_text(encoding="utf-8"))
        output=Path(q["output"]);template=Path(q["template"])
        if output.exists() or template.exists():raise RuntimeError("Fresh output paths required")
        pres.SlideMaster.ApplyTheme(str(Path("C:/Program Files/Microsoft Office/root/Document Themes 16/Office Theme.thmx").resolve()))
        colors=["162E3B","FFFFFF","102A38","F5F3ED","117A7E","65D2C2","D4A054","9AB1B3","536876","CEDCD8","117A7E","D4A054"]
        for i,color in enumerate(colors,1):pres.SlideMaster.Theme.ThemeColorScheme.Colors(i).RGB=rgb(color)
        record["operations"].append(dict(kind="native-theme",source="Office Theme.thmx",custom_palette=colors))
        native_layouts={}
        for name,bg,title_color in [("Editorial Cover","102A38","FFFFFF"),("Editorial Light","F5F3ED","162E3B"),("Editorial Dark","102A38","FFFFFF"),("Editorial Section","F5F3ED","162E3B")]:
            layout=pres.SlideMaster.CustomLayouts.Add(pres.SlideMaster.CustomLayouts.Count+1)
            layout.Name=name;layout.DisplayMasterShapes=False;layout.FollowMasterBackground=False
            for j in range(layout.Shapes.Count,0,-1):layout.Shapes.Item(j).Delete()
            layout.Background.Fill.Solid();layout.Background.Fill.ForeColor.RGB=rgb(bg)
            if name=="Editorial Cover":layout.Background.Fill.UserPicture(str(ROOT/"assets/editorial-v2/hero.png"))
            if name=="Editorial Section":layout.Background.Fill.UserPicture(str(ROOT/"assets/editorial-v2/section.png"))
            rect=(.76,1.65,6.1,1.96) if name=="Editorial Cover" else (.68,.96,12,.85)
            placeholder(layout,1,rect,"Editable title",42 if name=="Editorial Cover" else 34,title_color)
            placeholder(layout,2,(.8,2.25,11.7,4.4),"Editable content",22,title_color)
            native_layouts[name]=layout
        record["operations"].append(dict(kind="native-master-layouts",names=list(native_layouts)))
        for number,page in enumerate(spec["slides"],1):
            slide=pres.Slides.Item(number)
            key="Editorial Cover" if number==1 else "Editorial Section" if number==9 else "Editorial Dark" if page["background_color"]=="102A38" else "Editorial Light"
            slide.CustomLayout=native_layouts[key]
            slide.DisplayMasterShapes=False
            # Empty placeholders inserted by assigning a layout are not scene content.
            for j in range(slide.Shapes.Count,0,-1):
                shape=slide.Shapes.Item(j)
                if shape.Type==14 and shape.HasTextFrame and not shape.TextFrame.HasText:shape.Delete()
            for e in page["elements"]:
                if e["type"]=="chart":
                    shape=slide.Shapes.Item(e["id"]);chart=shape.Chart;chart.ChartStyle=10
                    series=chart.SeriesCollection(1)
                    for point,color in [(1,"9AB1B3"),(2,"117A7E")]:
                        series.Points(point).Format.Fill.ForeColor.RGB=rgb(color)
                    record["operations"].append(dict(kind="native-chart-style",element_id=e["id"],style=chart.ChartStyle))
                if e["type"]=="diagram":
                    prior=slide.Shapes.Item(e["id"]);prior.Delete()
                    r=e["rect"];labels=e["diagram"]["nodes"];names=[];step=r["w"]/len(labels)
                    for i,text in enumerate(labels):
                        node=slide.Shapes.AddShape(52,(r["x"]+i*step)*72,r["y"]*72,(step-.06)*72,r["h"]*72)
                        node.Name=e["id"]+f"-node-{i+1}";names.append(node.Name)
                        node.Fill.ForeColor.RGB=rgb("117A7E" if i<3 else "102A38")
                        node.Line.Visible=False
                        node.TextFrame.TextRange.Text=text
                        node.TextFrame.TextRange.Font.Name="Microsoft YaHei"
                        node.TextFrame.TextRange.Font.Size=22
                        node.TextFrame.TextRange.Font.Color.RGB=rgb("FFFFFF")
                        node.TextFrame.TextRange.ParagraphFormat.Alignment=2
                        node.TextFrame.VerticalAnchor=3
                        node.TextFrame.MarginLeft=0;node.TextFrame.MarginRight=0
                        node.TextFrame.MarginTop=0;node.TextFrame.MarginBottom=0
                        node.TextFrame.WordWrap=False
                    shape=slide.Shapes.Range(names).Group();shape.Name=e["id"]
                    record["operations"].append(dict(kind="native-grouped-process",element_id=e["id"],nodes=labels,shape_type="msoShapeChevron",smartart=False))
                if e["type"]=="smartart":
                    prior=slide.Shapes.Item(e["id"]);prior.Delete()
                    selected=next((x for x in layouts if x["id"].split("#")[0].endswith("/chevron1")),None)
                    if selected is None:selected=next(x for x in layouts if x["id"].split("#")[0].endswith("/process1"))
                    layout=app.SmartArtLayouts.Item(selected["id"])
                    r=e["rect"];shape=slide.Shapes.AddSmartArt(layout,*[r[k]*72 for k in ["x","y","w","h"]]);shape.Name=e["id"]
                    smart=shape.SmartArt;nodes=smart.Nodes
                    while nodes.Count<len(e["smartart"]["nodes"]):nodes.Add()
                    while nodes.Count>len(e["smartart"]["nodes"]):nodes.Item(nodes.Count).Delete()
                    for i,text in enumerate(e["smartart"]["nodes"],1):
                        tr=nodes.Item(i).TextFrame2.TextRange;tr.Text=text;tr.Font.Name="Microsoft YaHei";tr.Font.Size=22
                    smart.QuickStyle=app.SmartArtQuickStyles.Item(1)
                    smart.Color=app.SmartArtColors.Item(4)
                    record["operations"].append(dict(kind="native-smartart",element_id=e["id"],layout=selected,nodes=[nodes.Item(i).TextFrame2.TextRange.Text for i in range(1,nodes.Count+1)]))
        pres.SaveAs(str(output),24)
        pres.SaveCopyAs(str(template),26)
        record["slide_layouts"]=[dict(slide=i,name=pres.Slides.Item(i).CustomLayout.Name) for i in range(1,pres.Slides.Count+1)]
        record.update(status="completed",slide_count=pres.Slides.Count,template_format="potx, ppSaveAsOpenXMLTemplate=26")
        native_layouts.clear();shape=None;chart=None;series=None;smart=None;nodes=None;node=None;tr=None;slide=None;layout=None;prior=None
    else:raise ValueError("Unknown operation")
except Exception as exc:record.update(error=f"{type(exc).__name__}: {exc}")
finally:
    if pres is not None:
        try:pres.Close()
        except Exception as exc:record["cleanupError"]=str(exc)
        pres=None
    if app is not None and owned:
        try:
            if app.Presentations.Count==0:app.Quit()
            else:record["cleanupError"]="Unexpected other presentation; application retained"
        except Exception as exc:record["cleanupError"]=str(exc)
    app=None;gc.collect();pythoncom.CoUninitialize()
    record["cleanupCompleted"]="cleanupError" not in record
    report_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
raise SystemExit(0 if record["status"]=="completed" and record["cleanupCompleted"] else 1)
