"""Paired real OOXML fixtures; targeted rules, not implementation mirrors."""
from datetime import datetime
import json
from pathlib import Path
import unittest
import uuid
import zipfile
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches,Pt
from ppt_workflow.qa.inspect import inspect_deck
from ppt_workflow.qa.package import check_package
from ppt_workflow.qa.fonts import DEFAULT_RESOLVER
from ppt_workflow.qa.geometry import check_geometry
from ppt_workflow.contracts import validate

ROOT=Path(__file__).resolve().parents[1]


def make_deck():
    prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
    return prs,slide


def text(slide,value="Short text",*,x=1,y=2,w=4,h=1,size=18,face="Calibri",bold=False,color=(0,0,0)):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    frame=shape.text_frame; frame.margin_left=frame.margin_right=frame.margin_top=frame.margin_bottom=0
    frame.word_wrap=True
    run=frame.paragraphs[0].add_run(); run.text=value
    run.font.name=face; run.font.size=Pt(size); run.font.bold=bold; run.font.color.rgb=RGBColor(*color)
    return shape


def patch_zip(source,destination,changes):
    with zipfile.ZipFile(source) as z:
        parts={name:z.read(name) for name in z.namelist()}
    for name,value in changes.items():
        if value is None:
            parts.pop(name,None)
        else:
            parts[name]=value.encode() if isinstance(value,str) else value
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as z:
        for name,value in parts.items():
            z.writestr(name,value)


class QATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT/"runs"/("p1-qa-tests-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6])
        cls.root.mkdir(parents=True)
        cls.records=[]

    @classmethod
    def tearDownClass(cls):
        (cls.root/"fixture-results.json").write_text(json.dumps(cls.records,ensure_ascii=False,indent=2),encoding="utf-8")

    def inspect(self,name,prs):
        path=self.root/(self._testMethodName+"-"+name+".pptx"); prs.save(path)
        report=inspect_deck(path)
        self.assertEqual([],validate(report.qa,"qa"))
        self.records.append({"test":self._testMethodName,"variant":name,"path":str(path),"rules":sorted({i["rule"] for i in report.qa["issues"]}),"unknown":report.qa["coverage"]["unknown"]})
        return report

    def assert_rule(self,report,rule,expected):
        self.assertEqual(expected,any(i["rule"]==rule for i in report.qa["issues"]),report.qa["issues"])

    def pair(self,rule,good,bad):
        for name,setup,expected in [("good",good,False),("bad",bad,True)]:
            prs,slide=make_deck(); setup(slide)
            self.assert_rule(self.inspect(name,prs),rule,expected)

    def test_01_plain_text_and_inherited_background(self):
        prs,slide=make_deck(); text(slide)
        self.assert_rule(self.inspect("explicit",prs),"low-contrast",False)
        slide.element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}cSld').remove(slide.element.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}bg'))
        report=self.inspect("inherited",prs)
        self.assertFalse(any("exception" in u for u in report.qa["coverage"]["unknown"]))
        self.assert_rule(report,"low-contrast",False)

    def test_02_nontext_object_boundary(self):
        self.pair("off-slide",lambda s:s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(1),Inches(2),Inches(1),Inches(1)),lambda s:s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(14),Inches(2),Inches(1),Inches(1)))

    def test_03_text_object_boundary(self):
        self.pair("off-slide",lambda s:text(s),lambda s:text(s,x=-1))

    def test_04_nested_group_boundary(self):
        def setup(s,outside):
            g=s.shapes.add_group_shape(); nested=g.shapes.add_group_shape()
            text(nested,x=14 if outside else 2)
        self.pair("off-slide",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_05_group_scaling_boundary(self):
        def setup(s,bad):
            group=s.shapes.add_group_shape(); text(group,w=1)
            group.width=Inches(2); group.left=Inches(12 if bad else 2)
        self.pair("off-slide",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_06_rotation_changes_geometric_boundary(self):
        def setup(s,bad):
            shape=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(0.05 if bad else 2),Inches(2),Inches(1),Inches(3)); shape.rotation=90
        self.pair("off-slide",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_07_intentional_crop_requires_allowlist(self):
        prs,s=make_deck(); shape=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(-1),0,Inches(15),Inches(7.5))
        path=self.root/"intentional-crop.pptx"; prs.save(path)
        eid=f"slide-1/shape-{shape.shape_id}"
        self.assert_rule(inspect_deck(path),"off-slide",True)
        self.assert_rule(inspect_deck(path,allow_outside=[eid]),"off-slide",False)

    def test_08_unbroken_word_width(self):
        self.pair("horizontal-overflow-risk",lambda s:text(s,"Word",w=2,h=3),lambda s:text(s,"W"*120,w=1,h=3))

    def test_09_wrap_disabled_width(self):
        def setup(s,bad):
            shape=text(s,"A phrase with several words",w=1 if bad else 8,h=3); shape.text_frame.word_wrap=False
        self.pair("horizontal-text-overflow",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_10_height_overflow(self):
        self.pair("text-overflow-risk",lambda s:text(s,"A\nB\nC",h=3),lambda s:text(s,"A\nB\nC",h=0.2))

    def test_11_paragraph_after_spacing(self):
        def setup(s,bad):
            shape=text(s,"First",h=0.8); shape.text_frame.paragraphs[0].space_after=Pt(50 if bad else 0)
            p=shape.text_frame.add_paragraph(); p.text="Second"; p.font.size=Pt(18); p.font.name="Calibri"
        self.pair("text-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_12_paragraph_before_spacing(self):
        def setup(s,bad):
            shape=text(s,"First",h=0.8); shape.text_frame.paragraphs[0].space_before=Pt(80 if bad else 0)
        self.pair("text-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_13_fixed_point_line_spacing(self):
        def setup(s,bad):
            shape=text(s,h=1); shape.text_frame.paragraphs[0].text="One\vTwo\vThree"
            shape.text_frame.paragraphs[0].font.size=Pt(18); shape.text_frame.paragraphs[0].font.name="Calibri"
            shape.text_frame.paragraphs[0].line_spacing=Pt(50 if bad else 18)
        self.pair("text-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_14_percentage_line_spacing(self):
        def setup(s,bad):
            shape=text(s,h=1); shape.text_frame.paragraphs[0].text="One\vTwo\vThree"
            shape.text_frame.paragraphs[0].font.size=Pt(18); shape.text_frame.paragraphs[0].font.name="Calibri"
            shape.text_frame.paragraphs[0].line_spacing=3.0 if bad else 1.0
        self.pair("text-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_15_missing_font(self):
        self.pair("font-not-installed",lambda s:text(s),lambda s:text(s,face="DefinitelyMissingP1Font"))

    def test_16_missing_glyph(self):
        self.pair("missing-glyph",lambda s:text(s,"ABC"),lambda s:text(s,"ABC\U0010ffff"))

    def test_17_font_style_and_immutable_resolution(self):
        normal=DEFAULT_RESOLVER.resolve("Calibri",False,False)
        bold=DEFAULT_RESOLVER.resolve("Calibri",True,False)
        absent=DEFAULT_RESOLVER.resolve("MissingAlias")
        self.assertFalse(normal.substituted); self.assertTrue(bold.bold)
        self.assertNotEqual(normal.path,bold.path); self.assertTrue(absent.substituted)
        self.assertFalse(DEFAULT_RESOLVER.resolve("Calibri",False,False).substituted)

    def test_18_mixed_run_small_text(self):
        def setup(s,bad):
            shape=text(s,"Normal",size=24)
            r=shape.text_frame.paragraphs[0].add_run(); r.text="tiny"; r.font.size=Pt(6 if bad else 24)
        self.pair("tiny-text",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_19_role_minimum(self):
        self.pair("role-font-size",lambda s:text(s,size=18),lambda s:text(s,size=11))

    def test_20_text_contrast(self):
        self.pair("low-contrast",lambda s:text(s,color=(0,0,0)),lambda s:text(s,color=(240,240,240)))

    def test_21_bold_14pt_large_text_rule(self):
        self.pair("low-contrast",lambda s:text(s,size=14,bold=True,color=(128,128,128)),lambda s:text(s,size=14,bold=False,color=(128,128,128)))

    def test_22_theme_color_resolution(self):
        def setup(s,bad):
            shape=text(s); run=shape.text_frame.paragraphs[0].runs[0]
            fill=run._r.get_or_add_rPr().find('{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
            for child in list(fill): fill.remove(child)
            color=OxmlElement("a:schemeClr"); color.set("val","lt1" if bad else "dk1"); fill.append(color)
        self.pair("low-contrast",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_23_merged_table_cell_width(self):
        def setup(s,bad):
            table=s.shapes.add_table(1,2,Inches(1),Inches(2),Inches(5),Inches(1)).table
            cell=table.cell(0,0); cell.merge(table.cell(0,1)); cell.text="W"*120 if bad else "Merged"
            for run in cell.text_frame.paragraphs[0].runs: run.font.size=Pt(18); run.font.name="Calibri"
        self.pair("horizontal-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_24_table_cell_height(self):
        def setup(s,bad):
            table=s.shapes.add_table(1,1,Inches(1),Inches(2),Inches(4),Inches(0.3 if bad else 2)).table
            table.cell(0,0).text="One\nTwo\nThree"
        self.pair("text-overflow-risk",lambda s:setup(s,False),lambda s:setup(s,True))

    def test_25_gradient_contrast_unknown(self):
        prs,s=make_deck(); shape=text(s)
        s.background.fill.gradient()
        report=self.inspect("gradient",prs)
        self.assertTrue(any("contrast-background-unknown" in u for u in report.qa["coverage"]["unknown"]))
        self.assertNotEqual("passed",report.qa["status"])

    def test_26_recorded_autofit_recomputes_width(self):
        prs,s=make_deck(); shape=text(s,"WWW",w=0.6,h=1,size=24)
        body=shape.text_frame._txBody.find('{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr')
        for child in list(body):
            if child.tag.endswith(("noAutofit","spAutoFit","normAutofit")): body.remove(child)
        norm=OxmlElement("a:normAutofit"); norm.set("fontScale","50000"); body.append(norm)
        self.assert_rule(self.inspect("scaled",prs),"horizontal-overflow-risk",False)
        norm.set("fontScale","100000")
        self.assert_rule(self.inspect("unscaled",prs),"horizontal-overflow-risk",True)

    def test_27_rotated_text_is_explicitly_unknown(self):
        prs,s=make_deck(); shape=text(s); shape.rotation=45
        report=self.inspect("rotated",prs)
        self.assertTrue(any("rotated-or-flipped-text" in u for u in report.qa["coverage"]["unknown"]))

    def test_28_text_collision_risk(self):
        self.pair("text-collision-risk",lambda s:(text(s,"First",y=2),text(s,"Second",y=4)),lambda s:(text(s,"First",y=2),text(s,"Second",y=2)))

    def test_29_unsafe_xml_rejected(self):
        prs,s=make_deck(); text(s)
        good=self.root/"safe-xml.pptx"; prs.save(good)
        bad=self.root/"unsafe-xml.pptx"
        patch_zip(good,bad,{"custom.xml":'<!DOCTYPE a [<!ENTITY x "unsafe">]><a>&x;</a>'})
        self.assertFalse(any(i["rule"]=="unsafe-or-malformed-xml" for i in check_package(good).issues))
        self.assertTrue(any(i["rule"]=="unsafe-or-malformed-xml" for i in check_package(bad).issues))

    def test_30_relationship_target(self):
        prs,s=make_deck(); text(s)
        good=self.root/"relationships-good.pptx"; prs.save(good)
        bad=self.root/"relationships-bad.pptx"
        with zipfile.ZipFile(good) as z: value=z.read("ppt/_rels/presentation.xml.rels").decode()
        patch_zip(good,bad,{"ppt/_rels/presentation.xml.rels":value.replace("slides/slide1.xml","slides/missing.xml")})
        self.assertFalse(any(i["rule"]=="broken-relationship-target" for i in check_package(good).issues))
        self.assertTrue(any(i["rule"]=="broken-relationship-target" for i in check_package(bad).issues))

    def test_31_chart_axis_reference(self):
        prs,s=make_deck(); text(s)
        base=self.root/"chart-base.pptx"; prs.save(base)
        def blob(reference,cross):
            return f'<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:chart><c:plotArea><c:barChart><c:axId val="{reference}"/></c:barChart><c:valAx><c:axId val="1"/><c:crossAx val="{cross}"/></c:valAx><c:catAx><c:axId val="2"/><c:crossAx val="1"/></c:catAx></c:plotArea></c:chart></c:chartSpace>'
        for label,ref,cross,expected in [("good",1,2,False),("bad",999,2,True)]:
            path=self.root/f"axis-{label}.pptx"; patch_zip(base,path,{"ppt/charts/chart1.xml":blob(ref,cross)})
            self.assertEqual(expected,any(i["rule"]=="undeclared-chart-axis" for i in check_package(path).issues))
        path=self.root/"cross-axis-bad.pptx"; patch_zip(base,path,{"ppt/charts/chart1.xml":blob(1,999)})
        self.assertTrue(any(i["rule"]=="undeclared-cross-axis" for i in check_package(path).issues))

    def test_32_missing_content_type(self):
        prs,s=make_deck(); text(s)
        base=self.root/"content-types-good.pptx"; prs.save(base)
        bad=self.root/"content-types-bad.pptx"; patch_zip(base,bad,{"media.p1asset":b"data"})
        self.assertFalse(any(i["rule"]=="missing-content-type" for i in check_package(base).issues))
        self.assertTrue(any(i["rule"]=="missing-content-type" for i in check_package(bad).issues))

    def test_33_invalid_zip(self):
        path=self.root/"not-a-zip.pptx"; path.write_bytes(b"not a zip")
        self.assertTrue(any(i["rule"]=="invalid-package" for i in check_package(path).issues))

    def test_34_old_axis_probe_is_detected(self):
        path=ROOT/"tests/fixtures/undeclared_axis_validator_probe.zip"
        self.assertTrue(any(i["rule"]=="undeclared-chart-axis" for i in check_package(path).issues))

    def test_35_old_geometry_and_word_probes(self):
        folder=ROOT/"tests/fixtures"
        for filename,rule in [("nontext_offslide.pptx","off-slide"),("group_offslide.pptx","off-slide"),("unbroken_long_word.pptx","horizontal-text-overflow")]:
            self.assert_rule(inspect_deck(folder/filename),rule,True)
        report=inspect_deck(folder/"inherited_background.pptx")
        self.assertFalse(any("inspection-exception" in u for u in report.qa["coverage"]["unknown"]))

    def test_36_inherited_static_objects_report_unknown(self):
        from copy import deepcopy
        prs,s=make_deck(); shape=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(14),Inches(2),Inches(1),Inches(1))
        s.slide_layout.slide_master.shapes._spTree.append(deepcopy(shape.element))
        s.shapes._spTree.remove(shape.element)
        report=self.inspect("master-static",prs)
        self.assertTrue(any("inherited-master-objects" in u for u in report.qa["coverage"]["unknown"]))


if __name__=="__main__": unittest.main()
