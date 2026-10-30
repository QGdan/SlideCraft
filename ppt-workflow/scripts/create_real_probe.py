"""Three-page native-text QA fixture, deliberately including an overflow."""
import argparse
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
parser=argparse.ArgumentParser()
parser.add_argument("output",type=Path)
args=parser.parse_args()
if args.output.exists():raise RuntimeError("Refuse to overwrite an existing fixture")
args.output.parent.mkdir(parents=True,exist_ok=True)
deck=Presentation();deck.slide_width=Inches(13.333);deck.slide_height=Inches(7.5)
for index,value in enumerate(["Plain text","Inherited background","W"*120]):
    slide=deck.slides.add_slide(deck.slide_layouts[6])
    if index!=1:
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
    shape=slide.shapes.add_textbox(Inches(1),Inches(2),Inches(1 if index==2 else 8),Inches(1))
    shape.text_frame.word_wrap=False
    para=shape.text_frame.paragraphs[0];para.text=value;para.font.name="Calibri";para.font.size=Pt(18)
deck.save(args.output)
