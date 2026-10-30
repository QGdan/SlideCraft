"""One-time pinned Tabler subset import; ordinary searches stay offline."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,urllib.request,argparse
ROOT=Path(__file__).resolve().parents[1]
COMMIT='a4ce1404bc6d24d3c365afe7b258d6bf6f48d62d'
# Curated Chinese annotations, not claimed to be upstream translations.
SELECTION=[
 ('school','学校与教育','education',['学校','教育','校园','学习']),
 ('book','书籍与阅读','education',['书籍','阅读','学习','资料']),
 ('microscope','显微镜与研究','research',['实验','研究','科学','检验']),
 ('flask','烧瓶与实验','research',['实验','研究','化学','试验']),
 ('users','团队与协作','team',['团队','协作','人员','合作']),
 ('route','路线与步骤','process',['流程','路线','步骤','路径']),
 ('target','目标与任务','process',['目标','任务','行动','规划']),
 ('chart-bar','柱图概念','data',['数据','柱图','统计','比较']),
 ('chart-line','趋势概念','data',['数据','趋势','折线','增长']),
 ('chart-pie','占比概念','data',['数据','占比','结构','比例']),
 ('database','数据存储','data',['数据','存储','数据库','资料']),
 ('file-text','文档与报告','research',['文档','报告','资料','整理']),
 ('checklist','清单与审核','process',['清单','审核','检查','验收']),
 ('calendar','日历与计划','process',['日历','计划','时间','日期']),
 ('clock','时钟与时长','process',['时间','时长','效率','进度']),
 ('tools','工具与实施','tools',['工具','实施','建设','维护']),
 ('bulb','想法与创新','tools',['想法','创新','方案','思路']),
 ('presentation','演示与汇报','education',['演示','汇报','讲解','课堂']),
 ('search','搜索与查找','research',['检索','搜索','查找','调研']),
 ('shield-check','安全与质量','process',['安全','质量','审核','保障']),
 ('leaf','自然与绿色','environment',['绿色','自然','环境','植物']),
 ('heart-handshake','互助与服务','team',['互助','服务','协作','公益']),
 ('arrow-right','方向与连接','process',['箭头','方向','连接','下一步']),
 ('award','成果与荣誉','education',['成果','荣誉','评价','奖励']),
]
def fetch(relative):
    url=f'https://raw.githubusercontent.com/tabler/tabler-icons/{COMMIT}/{relative}'
    req=urllib.request.Request(url,headers={'User-Agent':'ppt-workflow-local-import'})
    with urllib.request.urlopen(req,timeout=30) as response:return url,response.read()
def main():
    p=argparse.ArgumentParser();p.add_argument('--node',type=Path,required=True);p.add_argument('--sharp',type=Path,required=True);a=p.parse_args()
    dest=ROOT/'assets/icons/tabler-outline'
    if dest.exists():raise ValueError('Fresh subset directory required')
    # All downloads complete before writing the catalog.
    with ThreadPoolExecutor(max_workers=4) as pool:
        files=list(pool.map(lambda row:fetch('icons/outline/'+row[0]+'.svg'),SELECTION))
    license_url,license_bytes=fetch('LICENSE')
    dest.mkdir(parents=True);(dest/'LICENSE').write_bytes(license_bytes);rows=[]
    for (name,title,category,tags),(url,data) in zip(SELECTION,files):
        svg=dest/(name+'.svg');svg.write_bytes(data);png=dest/(name+'.png')
        # Render once with bundled sharp. Runtime preparation uses Pillow on this mask.
        js="const fs=require('fs');const sharp=require(process.argv[1]);const s=fs.readFileSync(process.argv[2],'utf8').replaceAll('currentColor','#162E3B');sharp(Buffer.from(s)).resize(256,256).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exitCode=1});"
        subprocess.run([str(a.node),'-e',js,str(a.sharp),str(svg),str(png)],check=True,capture_output=True)
        rows.append(dict(id='tabler:'+name,title=title,type='icon',path=png.relative_to(ROOT).as_posix(),svg_path=svg.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(png.read_bytes()).hexdigest(),svg_sha256=hashlib.sha256(data).hexdigest(),width_px=256,height_px=256,transparent=True,source_id='tabler-'+name,license_note='MIT; retain supplied Tabler copyright and license notice.',origin_record='assets/icons/tabler-outline/provenance.json',style_family='tabler-outline',category=category,tags=[name,*tags],uses=['icon','concept','process'],negative_space='transparent',recommended_focus={'x':.5,'y':.5},preferred_fit='contain',placement_note='统一线性图标，用于解释概念或流程节点；以实际内容形成主视觉。',limitations=['图标不是统计数据或现场证据','PPT使用透明PNG，原始SVG另存；不声称已转成原生形状'],aliases=[],upstream_url=url,upstream_commit=COMMIT))
    provenance=dict(repository='https://github.com/tabler/tabler-icons',commit=COMMIT,license_url=license_url,license_sha256=hashlib.sha256(license_bytes).hexdigest(),translation='Project-curated Chinese titles and tags',preview='256px transparent PNG rendered from original SVG with bundled sharp; no runtime sharp dependency',count=len(rows))
    (dest/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    catalog=ROOT/'assets/icons/library.json';catalog.write_text(json.dumps(dict(version='icon-library/1',assets=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(provenance,ensure_ascii=False))
if __name__=='__main__':main()
