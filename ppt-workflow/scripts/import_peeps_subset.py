"""One-time official CC0 figure import; selected SVG content is pinned by hash."""
from pathlib import Path
import argparse,hashlib,json,subprocess,urllib.request
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
FILES=[('peep-16','5e535216550b76cb4af21e3d_peep-16.svg'),('peep-73','5e535a2b8e24938384074dac_peep-73.svg')]
PREFIX='https://cdn.prod.website-files.com/5e51c674258ffe10d286d30a/'
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ppt-workflow-local-import'}),timeout=30) as r:return r.read()
def main():
    p=argparse.ArgumentParser();p.add_argument('--node',type=Path,required=True);p.add_argument('--sharp',type=Path,required=True);a=p.parse_args()
    dest=ROOT/'assets/illustrations/open-peeps'
    if dest.exists():raise ValueError('Fresh illustration directory required')
    page=fetch('https://www.openpeeps.com/');license_bytes=fetch('https://creativecommons.org/publicdomain/zero/1.0/legalcode.en')
    svgs=[fetch(PREFIX+filename) for _,filename in FILES]
    dest.mkdir(parents=True);(dest/'source-page.html').write_bytes(page);(dest/'CC0-legalcode.html').write_bytes(license_bytes)
    provenance=dict(source_page='https://www.openpeeps.com/',license_url='https://creativecommons.org/publicdomain/zero/1.0/legalcode.en',license='CC0-1.0',author='Pablo Stanley',retrieved_on='2026-10-19',source_page_sha256=hashlib.sha256(page).hexdigest(),license_sha256=hashlib.sha256(license_bytes).hexdigest(),version='No upstream version published for these website assets; original SVG SHA256 pins exact content',preview='Original SVG rendered with bundled sharp, maximum 1024px; no runtime sharp dependency')
    (dest/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for (name,filename),data in zip(FILES,svgs):
        svg=dest/(name+'.svg');svg.write_bytes(data);png=dest/(name+'.png')
        js="const sharp=require(process.argv[1]);sharp(process.argv[2],{density:144}).resize(1024,1024,{fit:'inside'}).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exitCode=1});"
        subprocess.run([str(a.node),'-e',js,str(a.sharp),str(svg),str(png)],check=True,capture_output=True)
        with Image.open(png) as im:w,h=im.size
        rows.append(dict(id='peeps:'+name,title='人物插画 '+name,type='illustration',path=png.relative_to(ROOT).as_posix(),svg_path=svg.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(png.read_bytes()).hexdigest(),svg_sha256=hashlib.sha256(data).hexdigest(),width_px=w,height_px=h,transparent=True,source_id='peeps-'+name,license_note='CC0-1.0; official Open Peeps dedication by Pablo Stanley, retained with source page and legal code.',origin_record='assets/illustrations/open-peeps/provenance.json',style_family='open-peeps',category='people',tags=['人物','插画','角色','人像',name],uses=['figure','concept','case'],negative_space='transparent',recommended_focus={'x':.5,'y':.5},preferred_fit='contain',placement_note='人物组件按原比例完整显示；可与原生图表/流程配合，不表示真实人物或真实现场。',limitations=['人物素材，不是完整场景或活动照片','PNG内部不可原生编辑，SVG源文件另存'],aliases=[],upstream_url=PREFIX+filename))
    (ROOT/'assets/illustrations/library.json').write_text(json.dumps(dict(version='illustration-library/1',assets=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Imported 2 official Open Peeps SVGs and CC0/source records; visual curation still required')
if __name__=='__main__':main()
