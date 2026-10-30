"""Narrow workaround for two verified PptxGenJS 4.0.1 emitter defects.

Never modify source PPTX files. Every edit is logged; unknown broken axes stay broken.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from defusedxml import ElementTree as ET
from lxml import etree
import hashlib

C="http://schemas.openxmlformats.org/drawingml/2006/chart"
CT="http://schemas.openxmlformats.org/package/2006/content-types"


def normalize(raw, output):
    raw,output=Path(raw),Path(output)
    if output.exists() or raw.resolve()==output.resolve(): raise ValueError("Fresh separate export required")
    edits=[]
    with ZipFile(raw) as zin, ZipFile(output,"w",ZIP_DEFLATED) as zout:
        names=set(zin.namelist())
        for info in zin.infolist():
            data=zin.read(info.filename)
            if info.filename=="[Content_Types].xml":
                ET.fromstring(data,forbid_dtd=True)
                root=etree.fromstring(data)
                for el in list(root):
                    part=el.get("PartName","").lstrip("/")
                    # Only the exact emitted missing secondary master declarations.
                    import re
                    if el.tag==f"{{{CT}}}Override" and re.fullmatch(r"ppt/slideMasters/slideMaster(?:[2-9]|[1-9][0-9]+)\.xml",part) and part not in names:
                        root.remove(el); edits.append(dict(part=info.filename,rule="remove-missing-secondary-master-override",target=part))
                data=etree.tostring(root,xml_declaration=True,encoding="UTF-8",standalone=True)
            elif info.filename.startswith("ppt/charts/chart") and info.filename.endswith(".xml"):
                ET.fromstring(data,forbid_dtd=True)
                root=etree.fromstring(data); ns={"c":C}
                declared={e.get("val") for e in root.xpath("//c:catAx/c:axId|//c:valAx/c:axId|//c:serAx/c:axId",namespaces=ns)}
                for plot in root.xpath("//c:barChart|//c:lineChart",namespaces=ns):
                    axes=plot.findall(f"{{{C}}}axId")
                    if len(axes)==3 and all(a.get("val") in declared for a in axes[:2]) and axes[2].get("val")=="2094734556" and "2094734556" not in declared:
                        plot.remove(axes[2]); edits.append(dict(part=info.filename,rule="remove-2d-extraneous-series-axis",target="2094734556"))
                data=etree.tostring(root,xml_declaration=True,encoding="UTF-8",standalone=True)
            zout.writestr(info,data)
    return dict(engine="pptxgenjs@4.0.1",raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),edits=edits)
