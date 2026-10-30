"""Template-driven revision: one consistent visual system for all ten layouts."""
import json
from copy import deepcopy
from pathlib import Path
from .design import Scene,demo_deck
from .assets import register_asset

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/"templates/unified-v3/design-system.json"


class UnifiedScene(Scene):
    def __init__(self,number,layout,title,message,profile):
        self.profile=profile;c=profile["colors"]
        t=dict(font=profile["font"],bg=c["background"],ink=c["ink"],muted=c["muted"],accent=c["accent"],rule=c["rule"],light=c["soft"],body=22)
        super().__init__(t,number,layout,title,message,{},["demo-report","ai-art"],"","所有耗时为示意设定，不含人工审核。来源：examples/demo-report-v1.json。概念图为AI生成图片；标题、数据和流程为原生对象。")
        self.s["background_color"]=c["background"]
        self.s["elements"]=[]

    def base(self,art=False):
        r=self.profile["regions"];z=self.profile["font_sizes"]
        self.text("教学报告自动化试点",*r["kicker"],z["kicker"],self.t["accent"],bold=True,role="caption")
        self.text(self.s["title"],*r["title"],z["title"],bold=True,role="title")
        self.rule(.7,1.9,11.9)
        self.text("数据为示意设定，非实测结果"+("；概念图为 AI 生成" if art else ""),*r["source"],z["source"],self.t["muted"],role="source")
        self.text(self.s["id"][1:],*r["page"],z["source"],self.t["muted"],role="source")

    def image(self,name,rect):
        p=ROOT/f"assets/unified-v3/{name}.png"
        a=register_asset(p,asset_id=name,source_id="ai-art",license_note="用户授权生成或修改的概念图，仅作为插图，非实测证据。")
        e=self.element("image","decoration",rect,asset_path=a["path"],asset_id=name);e["editability_requirement"]="raster_allowed"
        return a


def unified_deck():
    profile=json.loads(PROFILE.read_text(encoding="utf-8"));base,_=demo_deck("business");fm={f["id"]:f for f in base["facts"]};pages=[];assets=[]
    titles=["教学报告自动化试点方案","试点目标与责任边界","同口径的耗时示例","人工与自动汇总的分工","汇总时间的示意对比","报告生成与人工审核流程","四周试点安排","指标与计算口径","试点评估与下一步","试点审批事项"]
    for n,layout in enumerate(profile["layouts"],1):
        c=UnifiedScene(n,layout["key"],titles[n-1],titles[n-1],profile);c.base(n in [1,2,9])
        if n==1:
            assets.append(c.image("hero",(6.85,2.16,5.75,3.24)))
            c.text("保留人工审核的\n教学报告试点",.78,2.62,6.0,1.45,34,bold=True,role="title")
            c.text("教研组与信息化团队",.8,4.7,5.7,.56,22,c.t["muted"])
            c.text("试点讨论稿",.8,5.6,5.7,.5,18,c.t["accent"])
        elif n==2:
            c.text("汇总自动完成\n判断留给教师",.78,2.66,6.0,1.46,34,bold=True,role="title")
            c.text("覆盖成绩读取、指标统计与初稿生成。\n教学解释与签发由教师完成。",.8,4.72,6.2,1.12,22,c.t["muted"])
            assets.append(c.image("review",(7.35,2.14,4.5,4.5)))
        elif n==3:
            for x,key,label,color in [(.8,"before","人工汇总",c.t["muted"]),(7.0,"after","自动汇总",c.t["accent"])]:
                c.fact_text("{fact:"+key+"}",fm,x,2.58,5.45,1.25,56,color,bold=True,role="data")
                c.text(label,x,4.15,5.45,.6,22)
            c.rule(.8,5.12,11.7)
            c.fact_text("耗时比 {fact:ratio}",fm,.8,5.56,5.5,.7,28,c.t["accent"],bold=True,role="data")
            c.text("同一份周报、同一数据范围\n人工审核时间另行计量",7.0,5.45,5.5,.94,20,c.t["muted"])
        elif n==4:
            for x,label,key,body,color in [(.8,"人工汇总","before","逐项复制成绩\n手工统计指标\n教师解释并签发",c.t["muted"]),(7.0,"自动汇总","after","读取统一成绩表\n按规则生成初稿\n教师解释并签发",c.t["accent"])]:
                c.text(label,x,2.47,5.4,.65,28,color,bold=True,role="title")
                c.fact_text("汇总用时 {fact:"+key+"}",fm,x,3.43,5.4,.62,24,color,bold=True)
                c.text(body,x,4.59,5.4,1.62,22)
        elif n==5:
            c.text("周报汇总耗时（分钟）",.8,2.17,8.0,.46,20,c.t["muted"])
            c.element("chart","data",(.62,2.82,8.85,3.58),fact_refs=["before","after"],chart=dict(kind="bar",categories=["人工汇总","自动汇总"],series=[dict(name="汇总耗时",values=[40,1],fact_ids=["before","after"])],unit="分钟"))
            c.fact_text("{fact:saved}",fm,9.82,2.88,2.95,1.06,44,c.t["accent"],bold=True,role="data")
            c.text("示意节省时间",9.85,4.08,2.8,.58,20)
            c.text("仅计算汇总环节。\n实际收益需在\n试点中重新测量。",9.85,4.97,2.8,1.22,18,c.t["muted"])
        elif n==6:
            c.element("diagram","diagram",(.8,2.68,11.8,1.35),diagram=dict(kind="process",nodes=["成绩输入","规则汇总","初稿生成","教师审核"]))
            for i,text in enumerate(["教师确认范围","保留计算依据","附来源与口径","确认后签发"]):c.text(text,.85+i*2.97,4.64,2.7,.72,19,c.t["muted"])
            c.rule(.8,5.75,11.7);c.text("审核不通过时修订初稿，确认后才进入正式报告。",.8,6.03,11.7,.59,22)
        elif n==7:
            for i,(week,title,body) in enumerate([("第1周","口径确认","统一字段与指标"),("第2周","并行生成","人工与自动各做一份"),("第3周","差异核对","记录错误与修订"),("第4周","评估决策","决定继续或暂停")]):
                x=.8+i*3.03;c.text(week,x,2.55,2.75,.7,32,c.t["accent"],bold=True,role="title");c.rule(x,3.66,2.55,c.t["accent"])
                c.text(title,x,4.12,2.7,.65,24,bold=True);c.text(body,x,5.14,2.64,1.02,20,c.t["muted"])
        elif n==8:
            table=deepcopy(next(e["table"] for s in base["slides"] for e in s["elements"] if e["type"]=="table"))
            c.element("table","data",(.8,2.21,11.75,3.8),fact_refs=["before","after","saved","ratio"],table=table)
            c.text("各页沿用相同口径，审核耗时未计入。",.8,6.24,11.7,.5,20,c.t["muted"])
        elif n==9:
            c.text("报告正确\n审核可用",.8,2.74,3.5,1.47,34,bold=True,role="title")
            c.text("进入推广前，\n先核对试点结果。",.8,4.85,3.5,1.05,22,c.t["muted"])
            assets.append(c.image("section",(4.65,2.16,7.9,4.45)))
        elif n==10:
            c.text("建议批准一个教研组的四周试点",.8,2.45,11.6,.85,32,bold=True,role="title")
            for y,label,body in [(3.85,"范围","一类周报，使用脱敏成绩表"),(4.76,"负责人","教研组指定教师与信息化联络人"),(5.67,"复核","每周核对内容，试点结束汇总实际耗时")]:
                c.text(label,.8,y,2.0,.55,20,c.t["accent"],bold=True);c.text(body,3.08,y,9.35,.55,22)
        pages.append(c.s)
    base.update(job_id="p2-unified-v3",slides=pages,assets=assets)
    base["sources"].append(dict(id="ai-art",kind="file",locator="assets/unified-v3/prompts.json",is_demo=True))
    return base,profile


def check_unified_consistency(deck,path=None):
    from .qa.common import CheckResult
    from pptx import Presentation
    p=json.loads(PROFILE.read_text(encoding="utf-8"));r=CheckResult(evaluated=["uniform-background","shared-header-footer-grid","shared-header-font","artwork-content-region","native-template-layout-binding"])
    prs=Presentation(path) if path else None;regions=p["regions"];headers=[]
    for i,page in enumerate(deck["slides"]):
        kw=dict(slide_id=page["id"])
        if page.get("background_color")!=p["colors"]["background"]:r.add("inconsistent-background","Slide changed the frozen template background",**kw)
        for region,role in [("title","title"),("source","source"),("page","source")]:
            expected=dict(zip(["x","y","w","h"],regions[region]))
            candidates=[e for e in page["elements"] if e["type"]=="text" and e["role"]==role and e["rect"]==expected]
            if len(candidates)!=1:r.add("inconsistent-shared-region",f"Missing/duplicate {region} at the frozen position",**kw);continue
            e=candidates[0];font=e["style"]
            if font["font_face"]!=p["font"] or font["font_size_pt"]!=p["font_sizes"]["title" if region=="title" else "source"]:r.add("inconsistent-shared-font",f"Font differs for {region}",**kw)
            if prs:
                shape=next((s for s in prs.slides[i].shapes if s.name==e["id"]),None)
                if not shape:r.add("missing-shared-native-object",e["id"],**kw);continue
                actual=[float(v)/914400 for v in [shape.left,shape.top,shape.width,shape.height]]
                if max(abs(a-b) for a,b in zip(actual,regions[region]))>.002:r.add("native-shared-grid-drift",f"{region} moved in target application",**kw)
                if region=="title":headers.append(dict(slide=page["id"],bbox_in=actual))
        for e in page["elements"]:
            if e["type"]!="image":continue
            x,y,w,h=[e["rect"][k] for k in ["x","y","w","h"]];cx,cy,cw,ch=regions["content"]
            if x<cx-.001 or y<cy-.001 or x+w>cx+cw+.001 or y+h>cy+ch+.001:r.add("artwork-outside-template-region","Artwork crosses the shared content region",element_id=e["id"],**kw)
        if prs:
            wanted=next(l["name"] for l in p["layouts"] if l["key"]==page["layout"])
            if prs.slides[i].slide_layout.name!=wanted:r.add("wrong-native-template-layout","Native layout binding differs",**kw)
            if str(prs.slides[i].background.fill.fore_color.rgb)!=p["colors"]["background"]:r.add("native-background-drift","Actual Office background differs",**kw)
    r.details["native_headers"]=headers
    return r
