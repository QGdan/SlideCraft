"""Owned scene construction. Coordinates are independent of renderer internals."""
from copy import deepcopy

THEMES = {
    "academic": dict(name="学术", bg="FFFFFF", ink="172E43", muted="526474", accent="176C72", light="EAF4F3", rule="D3E0E2"),
    "business": dict(name="商务", bg="FAF9F6", ink="202B3C", muted="626876", accent="3159AD", light="E9EEF9", rule="D9DFE9"),
    "technical": dict(name="技术", bg="142332", ink="F4F7FA", muted="B7C8D6", accent="68DBCC", light="233B4C", rule="466071"),
}
for _theme in THEMES.values():
    _theme.update(font="Microsoft YaHei", title=32, body=22, label=18, source=11, chart_label=16)


def format_fact(fact):
    value = fact["value"]
    if isinstance(value, (float, int)):
        value = f"{value:g}"
    return f"{value}{fact['unit']}"


def render_template(template, facts):
    import re
    return re.sub(r"\{fact:([A-Za-z0-9_-]+)\}", lambda m: format_fact(facts[m[1]]), template)


class Scene:
    def __init__(self, theme, number, layout, title, message, content, sources, disclosure, notes):
        self.t = theme
        self.content=content; self.disclosure=disclosure
        self.s = dict(id=f"s{number:02}", title=title, message=message, layout=layout,
                      notes=notes, source_refs=sources, elements=[])
        self.n = 0

    def element(self, kind, role, rect, **payload):
        self.n += 1
        e = dict(id=f"{self.s['id']}-e{self.n:02}", type=kind, role=role,
                 rect=dict(zip(["x", "y", "w", "h"], rect)), editability_requirement="native", fact_refs=[])
        e.update(payload)
        self.s["elements"].append(e)
        return e

    def text(self, text, x, y, w, h, size=None, color=None, bold=False, role="body", group=None):
        e = self.element("text", role, (x,y,w,h), text=text,
                         style=dict(font_face=self.t["font"], font_size_pt=size or self.t["body"],
                                    color=color or self.t["ink"], bold=bold))
        if group: e["group_id"] = group
        return e

    def fact_text(self, template, facts, *args, **kw):
        import re
        e = self.text(render_template(template, facts), *args, **kw)
        e["text_template"] = template
        e["fact_refs"] = list(dict.fromkeys(re.findall(r"\{fact:([A-Za-z0-9_-]+)\}", template)))
        return e

    def rule(self, x,y,w, color=None):
        return self.element("line", "decoration", (x,y,w,.01), style={"color":color or self.t["rule"]})

    def base(self, title=True):
        if title:
            self.text(self.s["title"], .72,.55,11.9,.72,32,bold=True,role="title")
            self.rule(.72,1.52,11.9)
        self.text(self.disclosure, .72,6.98,10.8,.25,11,self.t["muted"],role="source")
        self.text(self.s["id"][1:],12.1,6.97,.45,.28,11,self.t["muted"],role="source")


def cover(sc, facts):
    sc.base(False)
    sc.text(sc.s["title"],.85,1.65,11.6,1.0,40,bold=True,role="title")
    sc.text(sc.content["subtitle"],.88,2.95,11,.7,26)
    sc.rule(.88,4.15,11.3)
    sc.text(sc.content["context"],.88,4.65,9,1.2,22,sc.t["muted"])


def takeaway(sc,facts):
    sc.base()
    sc.text(sc.content["headline"],.8,2.0,11.7,1.7,34,bold=True,role="title")
    sc.text(sc.content["body"],.83,4.42,11.5,1.25,24,sc.t["muted"])


def kpi(sc,facts):
    sc.base()
    for x, (key,label) in zip([.8,5.05,9.3],sc.content["metrics"]):
        sc.fact_text("{fact:"+key+"}",facts,x,2.32,3.25,1.05,40,sc.t["accent"],bold=True,role="data")
        sc.text(label,x,3.55,3.25,.6,22)
    sc.rule(.8,4.55,11.7)
    sc.text(sc.content["body"],.8,4.96,11.7,1.05,22,sc.t["muted"])


def comparison(sc,facts):
    sc.base()
    for x,(head,body,template) in zip([.85,7.0],sc.content["columns"]):
        sc.text(head,x,1.95,5.1,.65,28,bold=True,role="title")
        sc.fact_text(template,facts,x,2.93,5.1,.6,24,sc.t["accent"],bold=True)
        sc.text(body,x,4.0,5.1,1.9,22)


def chart_takeaway(sc,facts):
    sc.base()
    sc.text(sc.content["chart_title"],.85,1.85,7.5,.5,22)
    chart=deepcopy(sc.content["chart"])
    for series in chart["series"]:series["values"]=[facts[f]["value"] for f in series["fact_ids"]]
    sc.element("chart","data",(.85,2.48,7.65,3.86),fact_refs=list(dict.fromkeys(f for s in chart["series"] for f in s["fact_ids"])),chart=chart)
    sc.fact_text(sc.content["callout"],facts,9.1,2.76,3.3,1.0,40,sc.t["accent"],bold=True,role="data")
    sc.text(sc.content["label"],9.1,3.87,3.3,.55,22)
    sc.text(sc.content["body"],9.1,4.82,3.3,1.2,20,sc.t["muted"])


def process(sc,facts):
    sc.base()
    for i,(label,sub) in enumerate(sc.content["steps"]):
        x=.8+i*3.12; group=f"process-{i+1}"
        sc.element("shape","diagram",(x,2.48,2.5,1.0), group_id=group, style={"fill":sc.t["light"],"color":sc.t["accent"]})
        sc.text(label,x+.12,2.71,2.26,.5,22,bold=True,role="diagram",group=group)
        sc.text(sub,x,4.05,2.75,.9,18,sc.t["muted"])
        if i<3:
            e=sc.element("line","diagram",(x+2.58,2.97,.44,.01),style={"color":sc.t["accent"]})
            e["arrow_end"] = True
    sc.text(sc.content["body"],.8,5.61,11.7,.65,22)


def timeline(sc,facts):
    sc.base()
    for i,(week,title,body) in enumerate(sc.content["milestones"]):
        x=.8+i*3.12
        sc.text(week,x,2.3,2.7,.65,28,sc.t["accent"],bold=True,role="title")
        sc.rule(x,3.35,2.75,sc.t["accent"])
        sc.text(title,x,3.84,2.75,.6,22,bold=True)
        sc.text(body,x,4.72,2.75,1.2,20,sc.t["muted"])


def table(sc,facts):
    sc.base()
    table=deepcopy(sc.content["table"])
    for row,ids in zip(table["rows"],table["fact_ids"]):
        for i,fid in enumerate(ids):
            if fid:row[i]=format_fact(facts[fid])
    sc.element("table","data",(.85,2.05,11.65,3.72),fact_refs=list(dict.fromkeys(f for row in table["fact_ids"] for f in row if f)),table=table)
    sc.text(sc.content["body"],.85,6.1,11.65,.5,20,sc.t["muted"])


def divider(sc,facts):
    sc.base(False)
    sc.text(sc.content["section"],.85,1.67,2.3,1.03,40,sc.t["accent"],bold=True,role="title")
    sc.text(sc.s["title"],.85,3.05,11.6,1.0,38,bold=True,role="title")
    sc.text(sc.content["body"],.88,4.55,11.5,.8,24,sc.t["muted"])


def closing(sc,facts):
    sc.base()
    sc.text(sc.content["headline"],.85,2.02,11.5,1.1,32,bold=True,role="title")
    sc.text(sc.content["body"],.85,3.48,11.5,1.94,22)
    sc.text(sc.content["request"],.85,5.96,11.5,.55,24,sc.t["accent"],bold=True)


LAYOUTS = dict(cover=cover,takeaway=takeaway,kpi=kpi,comparison=comparison,chart_takeaway=chart_takeaway,
               process=process,timeline=timeline,table=table,divider=divider,closing=closing)

DEMO_CONTENT={
    "cover":dict(subtitle="一个保留人工审核的试点方案",context="试点讨论稿\n教研组与信息化团队"),
    "takeaway":dict(headline="自动汇总释放时间\n教师仍负责解释与签发",body="本试点只讨论报告生成环节。\n教学决策继续由教师结合课堂情况作出。"),
    "kpi":dict(metrics=[("before","人工汇总"),("after","自动汇总"),("ratio","耗时比")],body="同一份周报、相同数据范围\n耗时比按人工汇总时间除以自动汇总时间计算。"),
    "comparison":dict(columns=[("人工汇总","逐项复制成绩\n手工统计指标\n教师解释并签发","汇总用时：{fact:before}"),("自动汇总","读取同一份成绩表\n按规则生成初稿\n教师解释并签发","汇总用时：{fact:after}")]),
    "chart_takeaway":dict(chart_title="周报汇总耗时（分钟）",chart=dict(kind="bar",categories=["人工汇总","自动汇总"],unit="分钟",series=[dict(name="周报汇总",fact_ids=["before","after"])]),callout="{fact:saved}",label="示意节省时间",body="节省量只覆盖汇总。\n审核时间另行计量。"),
    "process":dict(steps=[("成绩输入","教师确认范围"),("规则汇总","保留计算依据"),("初稿生成","附来源与口径"),("教师审核","确认后签发")],body="审核未通过的初稿回到规则汇总环节修订。"),
    "timeline":dict(milestones=[("第1周","口径确认","统一字段与指标"),("第2周","并行生成","人工与自动各做一份"),("第3周","差异核对","记录错误与修改"),("第4周","评估决策","决定继续或暂停")]),
    "table":dict(table=dict(columns=["指标","示意值","口径说明"],rows=[["人工汇总","","同一份周报"],["自动汇总","","同一数据范围"],["节省时间","","人工耗时减自动耗时"],["耗时比","","人工耗时除以自动耗时"]],fact_ids=[[None,"before",None],[None,"after",None],[None,"saved",None],[None,"ratio",None]]),body="各页沿用相同口径，审核耗时未计入。"),
    "divider":dict(section="02",body="进入推广前，先确认报告正确、审核可用。"),
    "closing":dict(headline="建议批准一个教研组的四周试点",body="范围：一类周报，使用脱敏成绩表。\n负责人：教研组指定教师与信息化联络人。\n复核：每周核对内容，试点结束汇总实际耗时。",request="下一次决策依据是试点实测结果。"),
}


def compose_page(theme, number, layout, title, message, content, facts, source_refs, disclosure, notes=""):
    """Reusable constrained layout API; rejects excess rows rather than dropping them."""
    if layout not in LAYOUTS:raise ValueError(f"Unsupported layout {layout}")
    required=set(DEMO_CONTENT[layout])
    if set(content)!=required:raise ValueError(f"{layout} content requires exactly {sorted(required)}")
    for key,count in [("metrics",3),("columns",2),("steps",4),("milestones",4)]:
        if key in content and len(content[key])!=count:raise ValueError(f"{layout} requires {count} {key}")
    if layout=="table":
        t=content["table"]
        if len(t["columns"])!=3 or len(t["rows"])!=4:raise ValueError("P2 table layout supports exactly 3 columns and 4 data rows; use custom spec for others")
    sc=Scene(theme,number,layout,title,message,content,source_refs,disclosure,notes)
    LAYOUTS[layout](sc,facts)
    return sc.s


def demo_deck(theme_name, *, overrides=None):
    theme=deepcopy(THEMES[theme_name]); theme.update(overrides or {})
    source=dict(id="demo-report",kind="demo",locator="examples/demo-report-v1.json",is_demo=True)
    facts=[]
    for fid,value,unit,formula in [("before",40,"分钟",None),("after",1,"分钟",None),
                                   ("saved",39,"分钟",dict(op="subtract",inputs=["before","after"])),
                                   ("ratio",40,"倍",dict(op="divide",inputs=["before","after"]))]:
        f=dict(id=fid,source_id=source["id"],value=value,unit=unit,scope="同一份教学周报的汇总环节，不含人工审核",is_demo=True,
               locator=f"/facts/{fid}",period="示意场景，无实测时间",metric=fid)
        if formula: f["formula"]=formula
        facts.append(f)
    fm={f["id"]:f for f in facts}
    titles=["教学报告自动化","试点目标与责任边界","同口径的耗时示例","人工与自动汇总的分工","汇总时间的示意对比",
            "报告生成与审核流程","四周试点安排","指标与计算口径","试点评估与下一步","试点审批事项"]
    slides=[]
    for i,(layout,fn) in enumerate(LAYOUTS.items()):
        slides.append(compose_page(theme,i+1,layout,titles[i],titles[i],deepcopy(DEMO_CONTENT[layout]),fm,[source["id"]],
                                  "方案示例，数据为示意设定，非实测结果。来源：demo-report-v1",
                                  "方案演示材料。所有耗时均为人为设定的示意数据，不代表已测得性能。来源：demo-report-v1。"))
    deck=dict(schema_version="0.1",job_id=f"p2-{theme_name}",canvas=dict(width=13.333333,height=7.5,unit="in"),
              theme=theme_name,sources=[source],facts=facts,slides=slides)
    return deck,theme
