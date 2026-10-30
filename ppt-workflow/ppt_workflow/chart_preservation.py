"""Fail closed if a text-only WPS copy drops a source chart's embedded workbook."""
import posixpath
from zipfile import ZipFile
from defusedxml import ElementTree as ET
from pptx import Presentation
NS={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def charts(shapes):
    for shape in shapes:
        if shape.shape_type==6:yield from charts(shape.shapes)
        elif shape.has_chart:yield shape
def internal_workbook(archive,shape):
    part=str(shape.chart.part.partname).lstrip('/');root=ET.fromstring(archive.read(part),forbid_dtd=True);data=root.find('c:externalData',NS)
    if data is None:return None
    relpath=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels');rels=ET.fromstring(archive.read(relpath),forbid_dtd=True)
    rid=data.get('{'+NS['r']+'}id');rel=next((r for r in rels if r.get('Id')==rid),None)
    if rel is None or not rel.get('Target') or rel.get('TargetMode')=='External':return None
    target=posixpath.normpath(posixpath.join(posixpath.dirname(part),rel.get('Target'))).lstrip('/')
    if target not in archive.namelist():return None
    return archive.read(target)
def verify_workbook_preservation(source,output,pages):
    src,dst=Presentation(source),Presentation(output);issues=[];checked=[];uncompared=[]
    if len(dst.slides)!=len(pages):return dict(status='failed',issues=['Output slide count differs from selection'],checked=[],uncompared=[])
    with ZipFile(source) as a,ZipFile(output) as b:
        for n,page in enumerate(pages):
            dest={}
            for shape in charts(dst.slides[n].shapes):dest.setdefault(shape.name,[]).append(shape)
            for original in charts(src.slides[page-1].shapes):
                identity=dict(source_page=page,output_page=n+1,chart_name=original.name)
                old=internal_workbook(a,original)
                if old is None:uncompared.append(identity);continue
                matches=dest.get(original.name,[])
                if len(matches)!=1 or internal_workbook(b,matches[0]) is None:issues.append({**identity,'rule':'embedded-chart-workbook-lost'})
                else:checked.append(identity)
    return dict(status='failed' if issues else 'passed',issues=issues,checked=checked,uncompared=uncompared,scope='Presence of previously embedded workbooks only; values/type/native review remains required')
