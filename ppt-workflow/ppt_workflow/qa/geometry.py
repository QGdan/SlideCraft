"""Affine geometry for slide shapes, including nested group transforms."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pptx.enum.shapes import MSO_SHAPE_TYPE
from .common import CheckResult

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
EMU = 914400.0
IDENTITY = (1., 0., 0., 1., 0., 0.)


def multiply(a, b):
    return (a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5])


def translate(x, y):
    return (1., 0., 0., 1., x, y)


def transform_point(matrix, x, y):
    return matrix[0]*x+matrix[2]*y+matrix[4], matrix[1]*x+matrix[3]*y+matrix[5]


def bbox(matrix, x, y, w, h):
    points = [transform_point(matrix, px, py) for px,py in [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]]
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)


def orientation(cx, cy, degrees, flip_h=False, flip_v=False):
    angle = math.radians(degrees)
    rotate = (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0., 0.)
    flip = (-1. if flip_h else 1., 0., 0., -1. if flip_v else 1., 0., 0.)
    return multiply(multiply(translate(cx, cy), multiply(rotate, flip)), translate(-cx, -cy))


def xfrm_for(shape):
    for path in [f"{P}grpSpPr/{A}xfrm", f"{P}spPr/{A}xfrm", f"{P}xfrm"]:
        node = shape.element.find(path)
        if node is not None:
            return node
    return None


def rotation_for(shape):
    node = xfrm_for(shape)
    return float(node.get("rot", 0))/60000 if node is not None else float(shape.rotation or 0)


def group_matrix(shape):
    node = xfrm_for(shape)
    if node is None:
        raise ValueError("Group lacks transform")
    def pair(tag, keys):
        item = node.find(A+tag)
        if item is None:
            raise ValueError(f"Group transform lacks {tag}")
        return tuple(float(item.get(k, 0))/EMU for k in keys)
    ox,oy = pair("off", ["x","y"])
    ew,eh = pair("ext", ["cx","cy"])
    cx,cy = pair("chOff", ["x","y"])
    cw,ch = pair("chExt", ["cx","cy"])
    if cw <= 0 or ch <= 0:
        raise ValueError("Group has nonpositive child extents")
    scale = (ew/cw, 0., 0., eh/ch, 0., 0.)
    base = multiply(translate(ox,oy), multiply(scale, translate(-cx,-cy)))
    rotation = orientation(ox+ew/2, oy+eh/2, float(node.get("rot",0))/60000,
                           node.get("flipH") in {"1","true"}, node.get("flipV") in {"1","true"})
    return multiply(rotation, base)


@dataclass
class ShapeRecord:
    slide_id: str
    element_id: str
    shape: object
    matrix: tuple
    local_rect: tuple
    bounds: tuple
    text_geometry_supported: bool


def collect_shapes(prs):
    records = []
    result = CheckResult(evaluated=["all-shape-boundaries", "group-affine-transforms", "shape-rotation-bounds"])
    for slide_no, slide in enumerate(prs.slides,1):
        sid = f"slide-{slide_no}"
        for label,parent in [("layout",slide.slide_layout),("master",slide.slide_layout.slide_master)]:
            if any(not shape.is_placeholder for shape in parent.shapes):
                result.unknown.append(f"{sid}:inherited-{label}-objects-not-geometrically-inspected")
        def walk(shapes, parent, prefix):
            for shape in shapes:
                eid = f"{prefix}/shape-{shape.shape_id}"
                try:
                    x,y,w,h = [float(v)/EMU for v in [shape.left,shape.top,shape.width,shape.height]]
                    if not all(math.isfinite(v) for v in [x,y,w,h]):
                        raise ValueError("Non-finite shape geometry")
                    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                        matrix = multiply(parent,group_matrix(shape))
                        walk(shape.shapes,matrix,eid)
                        continue
                    node = xfrm_for(shape)
                    angle = rotation_for(shape)
                    own = orientation(x+w/2,y+h/2,angle,
                                      node is not None and node.get("flipH") in {"1","true"},
                                      node is not None and node.get("flipV") in {"1","true"})
                    matrix = multiply(parent,own)
                    b = bbox(matrix,x,y,w,h)
                    supported = abs(matrix[1])<1e-8 and abs(matrix[2])<1e-8 and matrix[0]>0 and matrix[3]>0
                    records.append(ShapeRecord(sid,eid,shape,matrix,(x,y,w,h),b,supported))
                except Exception as exc:
                    result.unknown.append(f"geometry:{eid}:{exc}")
        walk(slide.shapes,IDENTITY,sid)
    return records,result


def check_geometry(prs, allow_outside=()):
    records,result = collect_shapes(prs)
    sw,sh = prs.slide_width/EMU,prs.slide_height/EMU
    for record in records:
        x,y,w,h = record.bounds
        if x < -0.01 or y < -0.01 or x+w > sw+0.01 or y+h > sh+0.01:
            if record.element_id in allow_outside:
                result.add("intentional-crop", "Explicitly allowed off-slide crop", severity="info", slide_id=record.slide_id, element_id=record.element_id,bbox=record.bounds)
            else:
                result.add("off-slide", "Object crosses the slide canvas", slide_id=record.slide_id,element_id=record.element_id,bbox=record.bounds)
    result.details["shape_count"] = len(records)
    return records,result
