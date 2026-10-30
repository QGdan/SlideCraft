"""P2 revision: art-directed editorial sample with editable evidence layers."""
from pathlib import Path
from copy import deepcopy
from .design import Scene,demo_deck
from .assets import register_asset

ROOT=Path(__file__).resolve().parents[1]
PALETTE=dict(name="Editorial Teal",font="Microsoft YaHei",bg="F5F3ED",ink="162E3B",muted="536876",
             accent="117A7E",light="E2EFEB",rule="CEDCD8",title=34,body=22,label=18,source=11,chart_label=20)


class Canvas(Scene):
    def __init__(self,number,layout,title,message,*,dark=False):
        t=deepcopy(PALETTE)
        if dark:t.update(bg="102A38",ink="FFFFFF",muted="AFC5CE",accent="65D2C2",rule="395866")
        super().__init__(t,number,layout,title,message,{},["demo-report","ai-art"],"", "所有耗时为示意设定，不含人工审核。来源：examples/demo-report-v1.json。插图为AI生成概念图，非真实产品截图，提示词见assets/editorial-v2/prompts.json。")
        self.s["background_color"]=t["bg"]

    def header(self,kicker):
        self.text(kicker,.68,.38,11.8,.3,12,self.t["accent"],bold=True,role="caption")
        self.text(self.s["title"],.68,.96,12.0,.85,34,bold=True,role="title")

    def footer(self,art=False,color=None):
        self.text("数据为示意设定，非实测结果"+("；概念图为 AI 生成" if art else ""),.68,7.03,11.6,.24,11,color or self.t["muted"],role="source")
        self.text(self.s["id"][1:],12.13,7.02,.5,.26,11,color or self.t["muted"],role="source")

    def image(self,name,rect):
        a=register_asset(ROOT/f"assets/editorial-v2/{name}.png",asset_id=name,source_id="ai-art",license_note="用户授权生成的概念插图；不含第三方品牌；不作为事实证据。")
        e=self.element("image","background" if name in {"hero","section"} else "decoration",rect,asset_path=a["path"],asset_id=name)
        e["editability_requirement"]="raster_allowed"
        return a

    def panel(self,rect,fill,role="background"):
        return self.element("shape",role,rect,style=dict(fill=fill,color=fill))


def editorial_deck():
    base,_=demo_deck("business");facts={f["id"]:f for f in base["facts"]};pages=[];assets=[]
    c=Canvas(1,"cover","教学报告\n自动化试点","先减轻汇总工作，再评估实际效果",dark=True)
    assets.append(c.image("hero",(0,0,13.333333,7.5)))
    c.text("教学报告\n自动化试点",.76,1.65,6.1,1.96,42,"FFFFFF",bold=True,role="title")
    c.text("一个保留人工审核的试点方案",.8,4.13,6.05,.65,24,"E7F0EE")
    c.text("试点讨论稿",.8,.65,5,.4,14,"65D2C2",bold=True,role="caption")
    c.text("教研组与信息化团队",.8,5.77,5.9,.55,20,"BECFD4")
    c.footer(True,"BACBD1");pages.append(c.s)

    c=Canvas(2,"takeaway","试点目标与责任边界","自动汇总，教师解释并签发")
    c.header("01  目标与边界")
    c.text("汇总自动完成\n判断留给教师",.74,2.27,6.2,1.63,38,bold=True,role="title")
    c.rule(.74,4.22,5.9,c.t["accent"])
    c.text("覆盖成绩读取、指标统计与初稿生成。\n教学解释与签发由教师完成。",.74,4.73,6.4,1.15,22,c.t["muted"])
    assets.append(c.image("review",(7.14,1.9,5.48,5.48)))
    c.footer(True);pages.append(c.s)

    c=Canvas(3,"kpi","同口径的耗时示例","相同周报和相同范围的示意对比",dark=True)
    c.header("02  示意场景")
    c.fact_text("{fact:before}",facts,.8,2.28,5.45,1.32,60,c.t["muted"],bold=True,role="data")
    c.fact_text("{fact:after}",facts,7.15,2.28,5.35,1.32,60,c.t["accent"],bold=True,role="data")
    c.text("人工汇总",.82,3.89,5.2,.62,24)
    c.text("自动汇总",7.17,3.89,5.2,.62,24)
    c.rule(.8,4.92,11.7)
    c.fact_text("耗时比 {fact:ratio}",facts,.82,5.43,5.3,.72,28,c.t["accent"],bold=True,role="data")
    c.text("同一份周报、同一数据范围\n人工审核时间另行计量",7.17,5.3,5.25,1.08,20,c.t["muted"])
    c.footer();pages.append(c.s)

    c=Canvas(4,"comparison","教师职责保持在审核环节","工作方式改变，解释责任保留")
    c.header("03  工作分工")
    c.panel((0,2.04,6.65,4.42),"EBEFEB")
    for x,label,template,body,col in [(.8,"人工汇总","汇总用时 {fact:before}","逐项复制成绩\n手工统计指标\n教师解释并签发",c.t["muted"]),(7.27,"自动汇总","汇总用时 {fact:after}","读取统一成绩表\n按规则生成初稿\n教师解释并签发",c.t["accent"])]:
        c.text(label,x,2.55,5.2,.63,28,col,bold=True,role="title")
        c.fact_text(template,facts,x,3.45,5.15,.65,24,col,bold=True)
        c.text(body,x,4.54,5.05,1.53,22)
    c.footer();pages.append(c.s)

    c=Canvas(5,"chart_takeaway","汇总时间的示意对比","人工与自动汇总相差39分钟")
    c.header("04  时间对比")
    c.text("周报汇总耗时（分钟）",.8,2.07,8.1,.5,20,c.t["muted"])
    c.element("chart","data",(.62,2.76,8.85,3.58),fact_refs=["before","after"],chart=dict(kind="bar",categories=["人工汇总","自动汇总"],series=[dict(name="汇总耗时",values=[40,1],fact_ids=["before","after"])],unit="分钟"))
    c.fact_text("{fact:saved}",facts,9.82,2.74,2.95,1.06,44,c.t["accent"],bold=True,role="data")
    c.text("示意节省时间",9.85,4.01,2.8,.58,20)
    c.text("仅计算汇总环节。\n实际收益需在\n试点中重新测量。",9.85,4.91,2.8,1.22,18,c.t["muted"])
    c.footer();pages.append(c.s)

    c=Canvas(6,"process","报告生成与人工审核流程","审核未通过的初稿返回规则汇总环节")
    c.header("05  交付流程")
    c.element("diagram","diagram",(.75,2.4,11.8,1.58),diagram=dict(kind="process",nodes=["成绩输入","规则汇总","初稿生成","教师审核"]))
    for i,body in enumerate(["教师确认范围","保留计算依据","附来源与口径","确认后签发"]):
        c.text(body,.81+i*3.0,4.62,2.7,.74,19,c.t["muted"])
    c.rule(.8,5.8,11.7)
    c.text("审核不通过时修订初稿，确认后才进入正式报告。",.8,6.13,11.7,.59,22)
    c.footer();pages.append(c.s)

    c=Canvas(7,"timeline","四周试点安排","以并行生成和差异核对支持最终决策")
    c.header("06  实施节奏")
    for i,(period,title,body) in enumerate([("第1周","口径确认","统一字段与指标"),("第2周","并行生成","人工与自动各做一份"),("第3周","差异核对","记录错误与修订"),("第4周","评估决策","决定继续或暂停")]):
        x=.8+i*3.03
        c.text(period,x,2.52,2.75,.68,32,c.t["accent"],bold=True,role="title")
        c.rule(x,3.6,2.55,c.t["accent"])
        c.text(title,x,4.08,2.7,.67,24,bold=True)
        c.text(body,x,5.12,2.64,1.04,20,c.t["muted"])
    c.footer();pages.append(c.s)

    c=Canvas(8,"table","指标与计算口径","跨页复用同一口径，不把审核计入汇总")
    c.header("07  口径核对")
    table=deepcopy(next(e["table"] for s in base["slides"] for e in s["elements"] if e["type"]=="table"))
    c.element("table","data",(.8,2.08,11.75,3.84),fact_refs=["before","after","saved","ratio"],table=table)
    c.text("各页沿用相同口径，审核耗时未计入。",.8,6.2,11.7,.57,21,c.t["muted"])
    c.footer();pages.append(c.s)

    c=Canvas(9,"divider","试点评估与下一步","先确认报告正确，再判断是否推广")
    assets.append(c.image("section",(0,0,13.333333,7.5)))
    c.text("08  评估决策",.78,.47,6.5,.39,14,c.t["accent"],bold=True,role="caption")
    c.text("试点评估与下一步",.78,1.22,11.6,.92,38,bold=True,role="title")
    c.text("进入推广前，先确认报告正确、审核可用。",.8,2.36,11.4,.65,23,c.t["muted"])
    c.footer(True);pages.append(c.s)

    c=Canvas(10,"closing","试点审批事项","批准一个教研组、一个报告类型的四周试点",dark=True)
    c.text("试点四周\n再决定推广",.77,1.17,7.22,2.11,44,bold=True,role="title")
    c.rule(.8,3.88,11.7,c.t["accent"])
    c.text("范围",.82,4.42,2.12,.48,18,c.t["accent"],bold=True)
    c.text("一类周报，使用脱敏成绩表",3.1,4.39,9.36,.55,22)
    c.text("负责人",.82,5.21,2.12,.48,18,c.t["accent"],bold=True)
    c.text("教研组指定教师与信息化联络人",3.1,5.18,9.36,.55,22)
    c.text("复核",.82,6.0,2.12,.48,18,c.t["accent"],bold=True)
    c.text("每周核对内容，试点结束汇总实际耗时",3.1,5.97,9.36,.55,22)
    c.footer();pages.append(c.s)
    base.update(job_id="p2-editorial-v2",slides=pages,assets=assets)
    base["sources"].append(dict(id="ai-art",kind="file",locator="assets/editorial-v2/prompts.json",is_demo=True))
    return base,PALETTE
