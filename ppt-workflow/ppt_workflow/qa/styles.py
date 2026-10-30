"""Effective formatting for ordinary DrawingML text; unknown stays unknown."""
from __future__ import annotations

from colorsys import rgb_to_hls, hls_to_rgb
from defusedxml import ElementTree as ET
from .package import NS

A = f"{{{NS['a']}}}"
P = f"{{{NS['p']}}}"


def first(nodes, attribute, default=None):
    for node in nodes:
        if node is not None and node.get(attribute) is not None:
            return node.get(attribute)
    return default


class StyleContext:
    def __init__(self, slide):
        self.slide = slide
        self.layout = slide.slide_layout
        self.master = self.layout.slide_master
        self.palette = {}
        self.fonts = {}
        self.color_map = {"bg1":"lt1","tx1":"dk1","bg2":"lt2","tx2":"dk2"}
        for root in [self.master.element,self.layout.element,self.slide.element]:
            color_map = root.find(P+"clrMap")
            if color_map is not None:
                self.color_map.update(color_map.attrib)
            override = root.find(f"{P}clrMapOvr/{A}overrideClrMapping")
            if override is not None:
                self.color_map.update(override.attrib)
        try:
            theme = self.master.part.part_related_by(NS["r"]+"/theme")
            root = ET.fromstring(theme.blob,forbid_dtd=True)
            for slot in root.findall("a:themeElements/a:clrScheme/*",NS):
                color = list(slot)[0] if len(slot) else None
                if color is not None:
                    value = color.get("val") if color.tag == A+"srgbClr" else color.get("lastClr")
                    if value and len(value)==6:
                        self.palette[slot.tag.split("}")[-1]] = tuple(int(value[i:i+2],16) for i in [0,2,4])
            for kind in ["majorFont","minorFont"]:
                node = root.find(f"a:themeElements/a:fontScheme/a:{kind}",NS)
                if node is not None:
                    self.fonts[kind] = {tag: (node.find(A+tag).get("typeface") if node.find(A+tag) is not None else None) for tag in ["latin","ea"]}
                    for font in node.findall(A+"font"):
                        if font.get("script") == "Hans":
                            self.fonts[kind]["hans"] = font.get("typeface")
        except Exception:
            pass

    def color(self, container):
        if container is None:
            return None
        node = next((n for n in container if n.tag in {A+"srgbClr",A+"schemeClr",A+"sysClr"}),None)
        if node is None:
            return None
        if node.tag == A+"schemeClr":
            key = self.color_map.get(node.get("val"),node.get("val"))
            color = self.palette.get(key)
        else:
            value = node.get("val") if node.tag == A+"srgbClr" else node.get("lastClr")
            try:
                color = tuple(int(value[i:i+2],16) for i in [0,2,4]) if value and len(value)==6 else None
            except ValueError:
                color = None
        if color is None:
            return None
        for effect in node:
            tag = effect.tag.split("}")[-1]
            value = float(effect.get("val",100000))/100000
            if tag in {"alpha","alphaMod","alphaOff"}:
                if tag != "alpha" or value < 0.999:
                    return None
            elif tag == "tint":
                color = tuple(round(c+(255-c)*value) for c in color)
            elif tag == "shade":
                color = tuple(round(c*value) for c in color)
            elif tag in {"lumMod","lumOff"}:
                hue,light,sat = rgb_to_hls(*(c/255 for c in color))
                light = light*value if tag == "lumMod" else light+value
                color = tuple(round(c*255) for c in hls_to_rgb(hue,max(0,min(1,light)),sat))
            else:
                return None
        return color

    def fill(self, node):
        if node is None:
            return "inherit",None
        for child in node:
            if child.tag == A+"solidFill":
                color = self.color(child)
                return ("solid" if color else "unknown"),color
            if child.tag == A+"noFill":
                return "transparent",None
            if child.tag in {A+"gradFill",A+"blipFill",A+"pattFill",A+"grpFill"}:
                return "unknown",None
        return "inherit",None

    def background(self):
        for root in [self.slide.element,self.layout.element,self.master.element]:
            bg = root.find(f"{P}cSld/{P}bg")
            if bg is None:
                continue
            state,color = self.fill(bg.find(P+"bgPr"))
            if state == "solid":
                return color
            if state == "unknown":
                return None
            ref = bg.find(P+"bgRef")
            if ref is not None:
                # idx=1001 is the first theme background fill; other fills may
                # be gradients or effects and remain deliberately unknown.
                if ref.get("idx") == "1001":
                    return self.color(ref)
                return None
        return None

    def shape_fill(self, shape):
        return self.fill(shape.element.find(P+"spPr"))

    def paragraph_nodes(self, shape, para):
        level = int(para._p.find(A+"pPr").get("lvl",0)) if para._p.find(A+"pPr") is not None else 0
        nodes = [para._p.find(A+"pPr")]
        tx = shape.text_frame._txBody if getattr(shape,"has_text_frame",False) else None
        if tx is not None:
            nodes.append(tx.find(f"{A}lstStyle/{A}lvl{level+1}pPr"))
        try:
            idx = shape.placeholder_format.idx
            for collection in [self.layout.placeholders,self.master.placeholders]:
                match = next((p for p in collection if p.placeholder_format.idx==idx),None)
                if match is not None and match.has_text_frame:
                    p = match.text_frame.paragraphs[0]._p
                    nodes.extend([p.find(A+"pPr"),match.text_frame._txBody.find(f"{A}lstStyle/{A}lvl{level+1}pPr")])
            label = str(shape.placeholder_format.type).upper()
            kind = "titleStyle" if "TITLE" in label else "bodyStyle"
        except Exception:
            kind = "otherStyle"
        nodes.append(self.master.element.find(f"{P}txStyles/{P}{kind}/{A}lvl{level+1}pPr"))
        return [n for n in nodes if n is not None]

    def run_style(self, shape, para, run_node, text):
        pnodes = self.paragraph_nodes(shape,para)
        nodes = [run_node]+[p.find(A+"defRPr") for p in pnodes]
        cjk = any("\u3400"<=c<="\u9fff" for c in text)
        face = None
        for node in nodes:
            if node is None:
                continue
            tags = ["ea","latin"] if cjk else ["latin"]
            for tag in tags:
                font = node.find(A+tag)
                if font is not None and font.get("typeface"):
                    face = font.get("typeface")
                    break
            if face:
                break
        if face and face.startswith("+"):
            kind = "majorFont" if face.startswith("+mj") else "minorFont"
            family = self.fonts.get(kind,{})
            face = (family.get("hans") or family.get("ea") or family.get("latin")) if cjk else family.get("latin")
        size = float(first(nodes,"sz",1800))/100
        bold = first(nodes,"b","0") in {"1","true"}
        italic = first(nodes,"i","0") in {"1","true"}
        color = None
        for node in nodes:
            if node is not None and node.find(A+"solidFill") is not None:
                color = self.color(node.find(A+"solidFill"))
                break
        if color is None and not any(n is not None and n.find(A+"solidFill") is not None for n in nodes):
            style = shape.element.find(P+"style")
            ref = style.find(A+"fontRef") if style is not None else None
            color = self.color(ref) if ref is not None else self.palette.get(self.color_map.get("tx1","dk1"))
        return {"face": face or ("Microsoft YaHei" if cjk else "Calibri"), "size":size,"bold":bold,"italic":italic,"color":color,"cjk":cjk,"pnodes":pnodes}


def spacing(pnodes, tag, normal_pt, default=0):
    for node in pnodes:
        child = node.find(A+tag)
        if child is None:
            continue
        pts = child.find(A+"spcPts")
        pct = child.find(A+"spcPct")
        if pts is not None:
            return float(pts.get("val",0))/100
        if pct is not None:
            return normal_pt*float(pct.get("val",0))/100000
    return default
