"""Write explicit demonstration-only contract examples; does not build slides."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples"
OUT.mkdir(exist_ok=True)
source = {"id": "demo_data", "kind": "demo", "locator": "合约示例：示意数据，不代表真实业务结果", "is_demo": True}
brief = {"schema_version": "0.1", "job_id": "contract_demo", "topic": "教学数据平台：接口示意", "audience": "工作流阶段审核", "language": "zh-CN", "delivery_mode": "presented", "slide_count": 8, "aspect_ratio": "16:9", "theme": "academic", "sources": [source], "required_native_types": ["text", "chart", "table"], "constraints": ["所有数据明确标记为示意数据"]}
facts = [
    {"id": "manual_minutes", "source_id": "demo_data", "value": 40, "unit": "分钟/份", "scope": "端到端流程，示意", "is_demo": True},
    {"id": "platform_minutes", "source_id": "demo_data", "value": 1, "unit": "分钟/份", "scope": "端到端流程，示意", "is_demo": True}
]

def text_element(index, text):
    return {"id": f"s{index}_title", "type": "text", "role": "title", "rect": {"x": 0.6, "y": 0.6, "w": 12, "h": 0.8}, "editability_requirement": "native", "fact_refs": [], "text": text, "style": {"font_face": "Microsoft YaHei", "font_size_pt": 32}}

titles = ["教学数据平台（示意）", "报告生成耗时对比（示意）", "报告生成记录（示意）", "数据口径说明", "处理流程", "实施排期", "验证范围", "待审核事项"]
layouts = ["cover", "chart_takeaway", "table", "takeaway", "process", "timeline", "takeaway", "closing"]
slides = [{"id": f"s{i}", "title": title, "message": "这是接口示例，所有数据为示意", "layout": layout, "notes": "仅验证数据合同，不表示版式已实现。", "source_refs": ["demo_data"], "elements": [text_element(i, title)]} for i, (title, layout) in enumerate(zip(titles, layouts), 1)]
slides[1]["elements"].append({"id": "s2_chart", "type": "chart", "role": "data", "rect": {"x": 0.8, "y": 2, "w": 9, "h": 4}, "editability_requirement": "native", "fact_refs": ["manual_minutes", "platform_minutes"], "chart": {"kind": "column", "categories": ["手工流程", "平台流程"], "series": [{"name": "示意耗时", "values": [40, 1]}], "unit": "分钟/份"}})
slides[2]["elements"].append({"id": "s3_table", "type": "table", "role": "data", "rect": {"x": 0.8, "y": 2, "w": 10, "h": 3}, "editability_requirement": "native", "fact_refs": ["manual_minutes", "platform_minutes"], "table": {"columns": ["流程（示意）", "分钟/份"], "rows": [["手工", 40], ["平台", 1]]}})
deck = {"schema_version": "0.1", "job_id": "contract_demo", "canvas": {"width": 13.333, "height": 7.5, "unit": "in"}, "theme": "academic", "sources": [source], "facts": facts, "slides": slides}
qa = {"schema_version": "0.1", "job_id": "contract_demo", "revision": 0, "created_at": "2026-10-14T00:00:00+08:00", "status": "unverified", "artifact": {"path": "example-only-not-built.pptx", "sha256": "0" * 64}, "stages": {name: {"status": "unverified", "evidence": ["接口示例，未执行实际检查"], "reason": "not executed"} for name in ["package", "geometry", "typography", "content", "render", "visual", "editability"]}, "coverage": {"evaluated": [], "unknown": ["example-only"]}, "issues": []}
for name, document in [("brief", brief), ("deck", deck), ("qa", qa)]:
    (OUT / f"{name}.json").write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
print("Wrote three demonstration contracts; no PPTX generated.")
