"""Per-run text estimates, cells and color checks with visible uncertainty."""
from __future__ import annotations

from dataclasses import dataclass
import re
from pptx.enum.shapes import MSO_SHAPE_TYPE
from .common import CheckResult
from .fonts import DEFAULT_RESOLVER, CJK
from .geometry import bbox, EMU
from .styles import StyleContext, A, P, first, spacing


def contrast(foreground, background):
    def luminance(rgb):
        values = [c/255 for c in rgb]
        channels = [v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in values]
        return sum(v*w for v,w in zip(channels,[0.2126,0.7152,0.0722]))
    hi,lo = sorted([luminance(foreground),luminance(background)],reverse=True)
    return (hi+0.05)/(lo+0.05)


@dataclass
class TextBlock:
    record: object
    owner: object
    frame: object
    rect: tuple
    element_id: str
    margins: tuple
    is_cell: bool = False


def text_blocks(records):
    blocks = []
    for record in records:
        shape = record.shape
        if shape.has_text_frame and shape.text_frame.text.strip():
            tf = shape.text_frame
            blocks.append(TextBlock(record,shape,tf,record.local_rect,record.element_id,
                                    tuple(v/EMU for v in [tf.margin_left,tf.margin_right,tf.margin_top,tf.margin_bottom])))
        if shape.has_table:
            table = shape.table
            x,y,_,_ = record.local_rect
            row_y = y
            for r,row in enumerate(table.rows):
                col_x = x
                for c,col in enumerate(table.columns):
                    cell = table.cell(r,c)
                    if not cell.is_spanned and cell.text.strip():
                        w = sum(table.columns[k].width/EMU for k in range(c,min(c+cell.span_width,len(table.columns))))
                        h = sum(table.rows[k].height/EMU for k in range(r,min(r+cell.span_height,len(table.rows))))
                        blocks.append(TextBlock(record,shape,cell.text_frame,(col_x,row_y,w,h),f"{record.element_id}/cell-{r}-{c}",
                                                tuple(v/EMU for v in [cell.margin_left,cell.margin_right,cell.margin_top,cell.margin_bottom]),True))
                    col_x += col.width/EMU
                row_y += row.height/EMU
    return blocks


def tokenize(chars):
    tokens,word = [],[]
    for item in chars:
        ch = item["char"]
        if ch in "\n\v" or ch.isspace() or CJK.search(ch) or ch in "，。；：！？、（）【】":
            if word:
                tokens.append(word); word=[]
            tokens.append([item])
        else:
            word.append(item)
    if word:
        tokens.append(word)
    return tokens


def wrapped_lines(chars, avail_pt, wrap=True, indent_pt=0):
    lines,current,width = [],[],0.
    overwide = False
    limit = avail_pt-indent_pt
    for token in tokenize(chars):
        text = "".join(item["char"] for item in token)
        if text in "\n\v":
            lines.append(current); current=[]; width=0.; limit=avail_pt
            continue
        tw = sum(item["width"] for item in token)
        if not current and text.isspace():
            continue
        if not text.isspace() and tw > limit+0.01:
            overwide = True
        if wrap and current and width+tw > limit:
            lines.append(current); current=[]; width=0.; limit=avail_pt
            if text.isspace():
                continue
        current.extend(token); width+=tw
    if current or not lines:
        lines.append(current)
    return lines,overwide


def background_for(block, records, context):
    shape = block.record.shape
    if block.is_cell:
        # Table style inheritance is deliberately not guessed. Explicit tcPr
        # fill is supported below; otherwise report an unknown background.
        r,c = [int(v) for v in block.element_id.rsplit("cell-",1)[1].split("-")]
        cell = shape.table.cell(r,c)
        state,color = context.fill(cell._tc.find(A+"tcPr"))
        return color if state=="solid" else None
    own_state,own = context.shape_fill(shape)
    if own_state=="solid":
        return own
    if own_state=="unknown":
        return None
    ground = context.background()
    bx,by,bw,bh = block.record.bounds
    for record in records:
        if record is block.record:
            break
        if record.slide_id != block.record.slide_id:
            continue
        x,y,w,h = record.bounds
        intersect = min(x+w,bx+bw)>max(x,bx) and min(y+h,by+bh)>max(y,by)
        if not intersect:
            continue
        state,color = context.shape_fill(record.shape)
        if record.shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            ground = None
        elif state in {"solid","unknown"}:
            covers = x<=bx+0.005 and y<=by+0.005 and x+w>=bx+bw-0.005 and y+h>=by+bh-0.005
            ground = color if covers and state=="solid" else None
    return ground


def measure_block(block, context, resolver=DEFAULT_RESOLVER):
    x,y,w,h = block.rect
    ml,mr,mt,mb = block.margins
    avail = max(0.01,(w-ml-mr)*72)
    body = block.frame._txBody.find(A+"bodyPr")
    wrap = body is None or body.get("wrap","square") != "none"
    normal = body.find(A+"normAutofit") if body is not None else None
    scale = float(normal.get("fontScale",100000))/100000 if normal is not None else 1.
    scale = max(0.1,min(1.,scale))
    unknown = []
    if normal is not None and normal.get("fontScale") is None:
        unknown.append("unresolved-autofit")
    if body is not None and (body.get("rot","0")!="0" or body.get("vert","horz")!="horz" or int(body.get("numCol",1))>1):
        unknown.append("rotated-vertical-or-multicolumn-text")
    warp = body.find(A+"prstTxWarp") if body is not None else None
    if warp is not None and warp.get("prst")!="textNoShape":
        unknown.append("wordart-text-warp")
    height,max_width,line_count = 0.,0.,0
    styles,missings,faces = [],set(),[]
    overwide = False
    for paragraph in block.frame.paragraphs:
        chars = []
        for child in paragraph._p:
            if child.tag not in {A+"r",A+"fld",A+"br"}:
                continue
            text = child.find(A+"t")
            value = "\n" if child.tag==A+"br" else text.text or "" if text is not None else ""
            if not value:
                continue
            style = context.run_style(block.owner,paragraph,child.find(A+"rPr"),value)
            face = resolver.resolve(style["face"],style["bold"],style["italic"],style["cjk"])
            styles.append(style | {"scaled_size":style["size"]*scale})
            faces.append(face)
            if face.substituted:
                unknown.append(f"substituted-font:{style['face']}->{face.family}")
            if face.style_missing:
                unknown.append(f"font-style-not-installed:{style['face']}")
            for character in value:
                size = style["size"]*scale
                width,missing = face.measure(character,size)
                missings.update(missing)
                chars.append({"char":character,"width":width,"height":size*face.line_ratio})
        pnodes = context.paragraph_nodes(block.owner,paragraph)
        normal_pt = max((item["height"] for item in chars),default=18*1.22)
        mar_l = float(first(pnodes,"marL",0))/12700
        mar_r = float(first(pnodes,"marR",0))/12700
        indent = float(first(pnodes,"indent",0))/12700
        if any(n.find(A+"buChar") is not None or n.find(A+"buAutoNum") is not None for n in pnodes):
            unknown.append("bullet-marker-width-approximate")
        lines,wide = wrapped_lines(chars,max(0.01,avail-mar_l-mar_r),wrap,max(0,indent))
        overwide = overwide or wide
        line_count += len(lines)
        pitches = [max((ch["height"] for ch in line),default=normal_pt) for line in lines]
        line_spacing = spacing(pnodes,"lnSpc",normal_pt,normal_pt)
        paragraph_height = (len(lines)-1)*line_spacing+pitches[-1]
        height += spacing(pnodes,"spcBef",normal_pt) + paragraph_height + spacing(pnodes,"spcAft",normal_pt)
        max_width = max(max_width,max((sum(ch["width"] for ch in line) for line in lines),default=0)+mar_l+max(0,indent))
    if missings:
        unknown.append("missing-font-glyphs")
    alignments = {first(context.paragraph_nodes(block.owner,p),"algn","l") for p in block.frame.paragraphs}
    if len(alignments)>1:
        unknown.append("mixed-paragraph-alignment")
    return {"height_in":height/72,"max_width_in":max_width/72,"line_count":line_count,
            "available_height_in":h-mt-mb,"available_width_in":w-ml-mr,
            "overwide_token":overwide,"wrap":wrap,"styles":styles,"missing":sorted(missings),
            "unknown":sorted(set(unknown)),"fonts":faces,"scale":scale,"alignment":next(iter(alignments),"l")}


def check_typography(prs, records, resolver=DEFAULT_RESOLVER, role_map=None):
    result = CheckResult(evaluated=["per-run-font-and-size","font-glyph-coverage","paragraph-spacing","point-line-spacing","table-cell-estimates","text-width-risk","text-contrast"],
                         unknown=["text-layout-is-heuristic-not-PowerPoint-shaping"])
    role_map = role_map or {}
    contexts = {f"slide-{i}":StyleContext(slide) for i,slide in enumerate(prs.slides,1)}
    measurements = []
    ink_boxes = []
    for block in text_blocks(records):
        record = block.record
        context = contexts[record.slide_id]
        location = dict(slide_id=record.slide_id,element_id=block.element_id,bbox=bbox(record.matrix,*block.rect))
        measured = measure_block(block,context,resolver)
        for item in measured["unknown"]:
            result.unknown.append(f"{block.element_id}:{item}")
        if not record.text_geometry_supported:
            result.unknown.append(f"{block.element_id}:rotated-or-flipped-text")
        if record.matrix[0]!=1 or record.matrix[3]!=1:
            result.unknown.append(f"{block.element_id}:scaled-group-text-layout")
        if block.is_cell:
            result.unknown.append(f"{block.element_id}:table-style-inheritance-not-fully-resolved")
        if measured["missing"]:
            result.add("missing-glyph", "Requested font lacks characters", severity="warning", characters=measured["missing"],**location)
        if any(face.substituted for face in measured["fonts"]):
            result.add("font-not-installed", "Requested font is substituted",severity="warning",**location)
        if measured["overwide_token"] or measured["max_width_in"] > measured["available_width_in"]+0.03:
            rule = "horizontal-overflow-risk" if measured["wrap"] else "horizontal-text-overflow"
            result.add(rule,"Text width estimate exceeds the available frame; confirm target renderer wrapping",severity="warning",needed_in=round(measured["max_width_in"],3),available_in=round(measured["available_width_in"],3),**location)
        if measured["height_in"] > measured["available_height_in"]*1.02 and measured["height_in"]-measured["available_height_in"]>0.08:
            result.add("text-overflow-risk","Estimated text height exceeds the available frame",severity="warning",needed_in=round(measured["height_in"],3),available_in=round(measured["available_height_in"],3),**location)
        ground = background_for(block,records,context)
        if ground is None:
            result.unknown.append(f"{block.element_id}:contrast-background-unknown")
        sizes = [s["scaled_size"] for s in measured["styles"]]
        inferred = "title" if max(sizes,default=0)>=24 and block.rect[1]<1.8 else "source" if block.rect[1]>6.3 and block.rect[3]<0.6 else "body"
        role = role_map.get(block.element_id,inferred)
        floor = {"title":28,"body":18,"caption":10,"source":10,"data":14}.get(role,18)
        for style in measured["styles"]:
            actual_size = style["scaled_size"]*abs(record.matrix[3]) if record.text_geometry_supported else style["scaled_size"]
            if actual_size < 9:
                result.add("tiny-text","Text is below the 9pt hard floor",point_size=actual_size,**location)
            elif actual_size < floor:
                result.add("role-font-size","Text is below the presented-mode role minimum",severity="warning",role=role,point_size=actual_size,minimum=floor,**location)
            color = style["color"]
            if color is None:
                result.unknown.append(f"{block.element_id}:text-color-unknown")
            elif ground is not None:
                ratio = contrast(color,ground)
                need = 3. if actual_size>=18 or (style["bold"] and actual_size>=14) else 4.5
                if ratio < need-0.005:
                    result.add("low-contrast","Text/background contrast is below configured guidance",ratio=round(ratio,3),required=need,**location)
        detail = {k:v for k,v in measured.items() if k not in {"fonts","styles"}}
        unique_fonts = {(f.requested,f.path,f.index,f.bold,f.italic):f for f in measured["fonts"]}
        detail.update(slide_id=record.slide_id,element_id=block.element_id,role=role,bounds_in=list(location["bbox"]),font_resolutions=[{"requested":f.requested,"resolved":f.family,"path":f.path,"bold":f.bold,"italic":f.italic,"substituted":f.substituted,"style_missing":f.style_missing} for f in unique_fonts.values()])
        measurements.append(detail)
        if record.text_geometry_supported and not measured["unknown"]:
            x,y,w,h = block.rect
            ml,mr,mt,mb = block.margins
            body = block.frame._txBody.find(A+"bodyPr")
            anchor = body.get("anchor","t") if body is not None else "t"
            slack = measured["available_height_in"]-measured["height_in"]
            shift = slack/2 if anchor=="ctr" else slack if anchor=="b" else 0
            ink_width = min(w-ml-mr,measured["max_width_in"])
            spare_width = w-ml-mr-ink_width
            xshift = spare_width/2 if measured["alignment"]=="ctr" else spare_width if measured["alignment"]=="r" else 0
            ink = bbox(record.matrix,x+ml+xshift,y+mt+shift,ink_width,measured["height_in"])
            ink_boxes.append((block,ink))
    for index,(first_block,first_box) in enumerate(ink_boxes):
        for second_block,second_box in ink_boxes[index+1:]:
            if first_block.record.slide_id!=second_block.record.slide_id or first_block.is_cell or second_block.is_cell:
                continue
            x1,y1,w1,h1 = first_box; x2,y2,w2,h2 = second_box
            ox = min(x1+w1,x2+w2)-max(x1,x2); oy=min(y1+h1,y2+h2)-max(y1,y2)
            if ox>0.15 and oy>0.075:
                result.add("text-collision-risk","Estimated text bands overlap; inspect rendered evidence",severity="warning",slide_id=first_block.record.slide_id,element_id=first_block.element_id,bbox=first_box,other_element=second_block.element_id)
    result.details["measurements"] = measurements
    result.unknown = sorted(set(result.unknown))
    return result
