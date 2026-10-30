"""Apply declared semantic groups and endpoint bindings without an Office session."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from defusedxml import ElementTree as SafeET

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
NS={'p':P,'a':A}
def q(ns,name):return f'{{{ns}}}{name}'

def structure_package(source,output,spec):
    source,output=Path(source),Path(output)
    if source.resolve()==output.resolve() or output.exists():raise ValueError('Fresh separate native structure output required')
    edits=[]
    with ZipFile(source) as zin,ZipFile(output,'w',ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if info.filename in {f'ppt/slides/slide{i}.xml' for i in range(1,len(spec['slides'])+1)}:
                number=int(info.filename.rsplit('slide',1)[1][:-4]);page=spec['slides'][number-1]
                if any(e.get('group_id') or e.get('connection') for e in page['elements']):
                    SafeET.fromstring(data,forbid_dtd=True)
                    root=E.fromstring(data);tree=root.find('p:cSld/p:spTree',NS)
                    shapes={el.find('.//p:cNvPr',NS).get('name'):el for el in tree if el.tag in {q(P,'sp'),q(P,'cxnSp'),q(P,'pic'),q(P,'graphicFrame')} and el.find('.//p:cNvPr',NS) is not None}
                    actualids={name:el.find('.//p:cNvPr',NS).get('id') for name,el in shapes.items()}
                    for e in page['elements']:
                        connection=e.get('connection')
                        if not connection:continue
                        el=shapes[e['id']];nv=el.find('p:nvSpPr',NS)
                        if el.tag!=q(P,'sp') or nv is None:raise ValueError('Only native line shapes can become bound connectors')
                        el.tag=q(P,'cxnSp');nv.tag=q(P,'nvCxnSpPr');old=nv.find('p:cNvSpPr',NS);old.tag=q(P,'cNvCxnSpPr')
                        for field,attr,site in [('stCxn','from_id','from_site'),('endCxn','to_id','to_site')]:
                            E.SubElement(old,q(A,field),id=actualids[connection[attr]],idx=str(connection[site]))
                        geom=el.find('p:spPr/a:prstGeom',NS)
                        if geom is None:raise ValueError('Connector preset geometry missing')
                        geom.set('prst',connection.get('geometry','line'))
                        if connection.get('flip_h'):el.find('p:spPr/a:xfrm',NS).set('flipH','1')
                        edits.append(dict(slide_id=page['id'],element_id=e['id'],action='bind-connector',from_id=connection['from_id'],to_id=connection['to_id']))
                    groups={}
                    for e in page['elements']:
                        if e.get('group_id'):groups.setdefault(e['group_id'],[]).append(e)
                    nextid=max(int(x.get('id')) for x in root.findall('.//p:cNvPr',NS))+1
                    for name,members in groups.items():
                        els=[shapes[e['id']] for e in members];positions=sorted(tree.index(el) for el in els)
                        if positions!=list(range(positions[0],positions[-1]+1)):raise ValueError('Semantic group objects must form a contiguous layer block')
                        ordered=[el for el in tree if el in els]
                        x=min(e['rect']['x'] for e in members);y=min(e['rect']['y'] for e in members)
                        w=max(e['rect']['x']+e['rect']['w'] for e in members)-x;h=max(e['rect']['y']+e['rect']['h'] for e in members)-y
                        emu=lambda value:str(round(value*914400))
                        group=E.Element(q(P,'grpSp'));nv=E.SubElement(group,q(P,'nvGrpSpPr'));E.SubElement(nv,q(P,'cNvPr'),id=str(nextid),name=name);nextid+=1
                        E.SubElement(nv,q(P,'cNvGrpSpPr'));E.SubElement(nv,q(P,'nvPr'));pr=E.SubElement(group,q(P,'grpSpPr'));xf=E.SubElement(pr,q(A,'xfrm'))
                        for tag,attrs in [('off',dict(x=emu(x),y=emu(y))),('ext',dict(cx=emu(w),cy=emu(h))),('chOff',dict(x=emu(x),y=emu(y))),('chExt',dict(cx=emu(w),cy=emu(h)))]:E.SubElement(xf,q(A,tag),**attrs)
                        tree.insert(positions[0],group)
                        for el in ordered:tree.remove(el);group.append(el)
                        edits.append(dict(slide_id=page['id'],group_id=name,action='native-group',members=[e['id'] for e in members]))
                    data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            zout.writestr(info,data)
    return dict(edits=edits)
