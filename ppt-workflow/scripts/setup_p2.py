"""Additive contract fields and canonical demo input, before P2 build."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ppt_workflow.design import demo_deck
schema_path=ROOT/"schemas/deck.schema.json"
schema=json.loads(schema_path.read_text(encoding="utf-8")); defs=schema["$defs"]
for key in ["locator","period","metric"]:
    defs["fact"]["properties"][key]=dict(type="string",minLength=1)
defs["fact"]["properties"]["formula"]=dict(type="object",additionalProperties=False,required=["op","inputs"],properties={
    "op":dict(enum=["divide","subtract"]),"inputs":dict(type="array",minItems=2,maxItems=2,items={"$ref":"#/$defs/id"})})
defs["element"]["properties"]["text_template"]=dict(type="string",minLength=1)
defs["element"]["properties"]["arrow_end"]=dict(type="boolean")
defs["chart"]["properties"]["series"]["items"]["properties"]["fact_ids"]=dict(type="array",items={"$ref":"#/$defs/id"})
defs["table"]["properties"]["fact_ids"]=dict(type="array",items=dict(type="array",items={"anyOf":[{"$ref":"#/$defs/id"},{"type":"null"}]}))
schema_path.write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
deck,theme=demo_deck("academic")
source=dict(id="demo-report-v1",description="人为设定的周报汇总耗时示意数据，无实测或商业效果声明。",
            facts={f["id"]:f for f in deck["facts"]})
out=ROOT/"examples/demo-report-v1.json"
if out.exists(): raise SystemExit("Canonical source already exists; review changes separately")
out.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
state_path=ROOT.parent/"06-实施与阶段审核/阶段状态.json"
state=json.loads(state_path.read_text(encoding="utf-8-sig"));state["active_stage"]="P2"
state["stages"]["P1"].update(review="approved",approval_evidence="用户于2026-10-14指示‘继续’，批准进入 P2")
state["stages"]["P2"].update(implementation="in_progress",review="not_submitted")
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
