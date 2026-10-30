import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree
from pptx import Presentation
from ppt_workflow.design import demo_deck,THEMES,LAYOUTS,compose_page,DEMO_CONTENT
from ppt_workflow.content import check_ledger,inspect_native,workbook_range
from ppt_workflow.export_fix import normalize
from ppt_workflow.contracts import validate
from ppt_workflow.qa.package import check_package
from ppt_workflow.assets import register_asset,check_assets
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SAMPLES=ROOT/"runs/p2-review-002"


class LedgerTests(unittest.TestCase):
    def setUp(self): self.deck,self.theme=demo_deck("academic")
    def rules(self):return {i["rule"] for i in check_ledger(self.deck).issues}
    def element(self,kind):return next(e for s in self.deck["slides"] for e in s["elements"] if e["type"]==kind and e.get("fact_refs"))
    def test_valid_ledger_resolves_original_records(self):self.assertEqual(check_ledger(self.deck,ROOT).status,"passed")
    def test_all_three_themes_cover_ten_layouts(self):
        for t in THEMES:
            d,_=demo_deck(t);self.assertFalse(validate(d,"deck")); self.assertEqual([s["layout"] for s in d["slides"]],list(LAYOUTS))
    def test_brand_colors_override_without_changing_facts(self):
        d,t=demo_deck("academic",overrides={"accent":"803A65","font":"Arial"});self.assertEqual(t["accent"],"803A65");self.assertEqual(d["facts"],self.deck["facts"])
    def test_reusable_layout_does_not_leak_demo_content(self):
        page=compose_page(self.theme,1,"cover","新项目", "新项目",dict(subtitle="新的副标题",context="新的汇报人"),{},["real-source"],"来源：项目材料","原始材料第1页")
        texts="\n".join(e.get("text","") for e in page["elements"])
        self.assertIn("新的副标题",texts);self.assertNotIn("教学报告",texts);self.assertNotIn("demo-report",texts)
    def test_excess_layout_items_are_rejected_not_truncated(self):
        content=copy.deepcopy(DEMO_CONTENT["kpi"]);content["metrics"].append(("saved","节省"))
        with self.assertRaises(ValueError):compose_page(self.theme,1,"kpi","标题","结论",content,{},["x"],"来源")
    def test_conflicting_fact_detected_by_semantic_key(self):
        f=copy.deepcopy(self.deck["facts"][0]);f.update(id="conflicting",value=41);self.deck["facts"].append(f);self.assertIn("fact-conflict",self.rules())
    def test_changed_source_record_is_detected(self):
        self.deck["facts"][0]["value"]=42; self.assertIn("source-fact-mismatch",{i["rule"] for i in check_ledger(self.deck,ROOT).issues})
    def test_derived_ratio_mismatch(self):self.deck["facts"][3]["value"]=45;self.assertIn("formula-mismatch",self.rules())
    def test_zero_denominator(self):self.deck["facts"][1]["value"]=0;self.assertIn("formula-zero-division",self.rules())
    def test_incompatible_units(self):self.deck["facts"][1]["unit"]="秒";self.assertIn("formula-scope-unit",self.rules())
    def test_changed_derived_period(self):self.deck["facts"][2]["period"]="不同范围";self.assertIn("formula-provenance",self.rules())
    def test_demo_cannot_claim_real_fact(self):self.deck["facts"][0]["is_demo"]=False;self.assertIn("demo-misrepresented",self.rules())
    def test_missing_source_disclosure(self):
        s=self.deck["slides"][0];s["elements"]=[e for e in s["elements"] if e["role"]!="source"];self.assertIn("demo-disclosure-missing",self.rules())
    def test_text_value_conflict(self):self.element("text")["text"]="41分钟";self.assertIn("text-fact-mismatch",self.rules())
    def test_unbound_duration_claim(self):
        self.deck["slides"][0]["elements"][-1]["text"]="生成耗时0.9秒";self.assertIn("unbound-numeric-claim",self.rules())
    def test_missing_text_template(self):self.element("text").pop("text_template");self.assertIn("text-binding-missing",self.rules())
    def test_chart_drift(self):self.element("chart")["chart"]["series"][0]["values"][1]=.9;self.assertIn("chart-fact-mismatch",self.rules())
    def test_chart_missing_binding(self):self.element("chart")["chart"]["series"][0].pop("fact_ids");self.assertIn("chart-binding-missing",self.rules())
    def test_chart_units_mismatch(self):self.element("chart")["chart"]["unit"]="秒";self.assertIn("chart-fact-mismatch",self.rules())
    def test_table_drift(self):self.element("table")["table"]["rows"][0][1]="42分钟";self.assertIn("table-fact-mismatch",self.rules())
    def test_missing_fact_metadata(self):self.deck["facts"][0].pop("period");self.assertIn("incomplete-fact-ledger",self.rules())
    def test_table_binding_dimensions(self):self.element("table")["table"]["fact_ids"].pop();self.assertIn("table-binding-missing",self.rules())
    def test_unknown_formula_input(self):self.deck["facts"][2]["formula"]["inputs"][0]="bad";self.assertIn("formula-input",self.rules())


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.deck,_=demo_deck("academic")
        self.directory=Path(tempfile.mkdtemp(prefix="p2-test-",dir=ROOT/"runs"))
        self.addCleanup(self.cleanup_directory)
        self.source=SAMPLES/"academic/deck.pptx"
        if not self.source.exists(): self.fail("P2 native fixture must be built before native integration tests")
    def cleanup_directory(self):
        import shutil
        target=self.directory.resolve()
        if not target.is_relative_to((ROOT/'runs').resolve()) or not target.name.startswith('p2-test-'):
            raise ValueError('Refused cleanup outside owned test directory')
        shutil.rmtree(target)
    def test_all_theme_objects_and_embedded_workbooks(self):
        for name in THEMES:
            d,_=demo_deck(name);r=inspect_native(SAMPLES/name/"deck.pptx",d)
            self.assertEqual(r.status,"passed",r.issues);self.assertEqual(len(r.details["mapping"]),sum(len(s["elements"]) for s in d["slides"]));self.assertTrue(r.details["charts"][0]["verified"])
    def test_raw_library_defects_fail_normalized_output_is_clean(self):
        raw=check_package(SAMPLES/"academic/raw.pptx");self.assertIn("dangling-content-type",{i["rule"] for i in raw.issues})
        self.assertIn("undeclared-chart-axis",{i["rule"] for i in raw.issues})
        output=self.directory/"fixed.pptx";log=normalize(SAMPLES/"academic/raw.pptx",output)
        self.assertEqual(len(log["edits"]),10);self.assertFalse(check_package(output).issues)
    def test_native_table_tampering_detected(self):
        p=Presentation(self.source);s=p.slides[7];next(sh for sh in s.shapes if sh.has_table).table.cell(1,1).text="99分钟"
        out=self.directory/"bad-table.pptx";p.save(out)
        self.assertIn("native-table-mismatch",{i["rule"] for i in inspect_native(out,self.deck).issues})
    def test_missing_object_identity_detected(self):
        p=Presentation(self.source);p.slides[0].shapes[0].name="unmapped";out=self.directory/"bad-map.pptx";p.save(out)
        self.assertIn("object-mapping",{i["rule"] for i in inspect_native(out,self.deck).issues})
    def mutate(self,part,change):
        out=self.directory/"mutation.pptx"
        with ZipFile(self.source) as z,ZipFile(out,"w",ZIP_DEFLATED) as dst:
            for info in z.infolist():
                b=z.read(info.filename);dst.writestr(info,change(b) if info.filename==part else b)
        return out
    def test_chart_cache_tampering_detected(self):
        def change(b):
            root=etree.fromstring(b);ns={"c":"http://schemas.openxmlformats.org/drawingml/2006/chart"}
            root.find(".//c:val/c:numRef/c:numCache/c:pt/c:v",ns).text="41";return etree.tostring(root)
        out=self.mutate("ppt/charts/chart1.xml",change)
        self.assertIn("native-chart-data-mismatch",{i["rule"] for i in inspect_native(out,self.deck).issues})
    def test_embedded_workbook_tampering_detected(self):
        def change(b):
            buf=io.BytesIO()
            with ZipFile(io.BytesIO(b)) as z,ZipFile(buf,"w",ZIP_DEFLATED) as dst:
                for info in z.infolist():
                    data=z.read(info.filename)
                    if info.filename=="xl/worksheets/sheet1.xml":
                        root=etree.fromstring(data);ns={"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                        root.find(".//s:c[@r='B2']/s:v",ns).text="41";data=etree.tostring(root)
                    dst.writestr(info,data)
            return buf.getvalue()
        out=self.mutate("ppt/embeddings/Microsoft_Excel_Worksheet1.xlsx",change)
        self.assertIn("native-chart-data-mismatch",{i["rule"] for i in inspect_native(out,self.deck).issues})
    def test_unknown_broken_axis_is_not_normalized_away(self):
        def change(b):return b.replace(b'<c:axId val="2094734554"/>',b'<c:axId val="999"/>',1)
        bad=self.mutate("ppt/charts/chart1.xml",change);fixed=self.directory/"not-hidden.pptx";log=normalize(bad,fixed)
        self.assertFalse(log["edits"]);self.assertIn("undeclared-chart-axis",{i["rule"] for i in check_package(fixed).issues})
    def test_unsupported_workbook_formula_rejected(self):
        with self.assertRaises(ValueError):workbook_range(b"", "Sheet1!A:A")
    def test_export_never_overwrites_input(self):
        with self.assertRaises(ValueError):normalize(self.source,self.source)
    def test_registered_raster_remains_local_image_with_same_bytes(self):
        image=self.directory/"image.png";Image.new("RGB",(8,8),"white").save(image)
        asset=register_asset(image,asset_id="img",source_id="demo-report",license_note="自建测试样本")
        self.deck["assets"]=[asset]
        self.deck["slides"][0]["elements"].append(dict(id="raster-test",type="image",role="caption",rect=dict(x=10,y=5,w=1,h=1),fact_refs=[],editability_requirement="raster_allowed",asset_id="img",asset_path=str(image)))
        self.assertEqual(check_assets(self.deck).status,"passed");self.assertFalse(validate(self.deck,"deck"))
        p=Presentation(self.source);from pptx.util import Inches
        sh=p.slides[0].shapes.add_picture(str(image),Inches(10),Inches(5),Inches(1),Inches(1));sh.name="raster-test"
        out=self.directory/"image.pptx";p.save(out)
        self.assertEqual(inspect_native(out,self.deck).status,"passed")
    def test_asset_hash_change_is_detected(self):
        image=self.directory/"image.png";Image.new("RGB",(8,8),"white").save(image)
        self.deck["assets"]=[register_asset(image,asset_id="img",source_id="demo-report",license_note="自建测试样本")]
        Image.new("RGB",(8,8),"black").save(image)
        self.assertIn("asset-integrity",{i["rule"] for i in check_assets(self.deck).issues})
    def test_asset_without_declared_permission_is_rejected(self):
        with self.assertRaises(ValueError):register_asset(self.directory/"unused",asset_id="img",source_id="demo-report",license_note=" ")
    def test_asset_unknown_origin_is_detected(self):
        image=self.directory/"image.png";Image.new("RGB",(8,8),"white").save(image)
        self.deck["assets"]=[register_asset(image,asset_id="img",source_id="unknown",license_note="自建测试样本")]
        self.assertIn("asset-origin",{i["rule"] for i in check_assets(self.deck).issues})
    def test_unregistered_image_is_rejected(self):
        self.deck["slides"][0]["elements"].append(dict(id="x",type="image",asset_path="missing.png"))
        self.assertIn("unregistered-raster-asset",{i["rule"] for i in check_assets(self.deck).issues})


if __name__=="__main__":unittest.main()
