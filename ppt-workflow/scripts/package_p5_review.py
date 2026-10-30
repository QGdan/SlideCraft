from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
OUT=PROJECT/'06-实施与阶段审核/P5-交付固化';TESTED=ROOT/'runs/p5-dist-003/ppt-workflow'
ACCEPT=TESTED/'runs/p5-acceptance';REPRO=ROOT/'runs/p5-final-repro'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
rows=read(ACCEPT/'results.json');repro=read(REPRO/'verification.json');install=read(ROOT/'runs/p5-global-installation.json')
assert repro['render_status']=='passed' and repro['portable_tests']==77
assert len(rows)==6 and sum(r['status']=='mechanically-passed' for r in rows)==5
log=(ROOT/'runs/p5-final-regression-tests.log').read_text(encoding='utf-8')
assert 'Ran 207 tests' in log and log.rstrip().endswith('OK')
old=read(PROJECT/'06-实施与阶段审核/P0/baseline-manifest.json')
changed=[r['path'] for r in old['originals'] if sha(PROJECT/r['path'])!=r['sha256']];assert not changed
dest=OUT/'样例';dest.mkdir(exist_ok=False)
visual=[]
for r in rows:
    if r['status']!='mechanically-passed':continue
    folder=dest/r['case'];folder.mkdir()
    shutil.copy2(r['deck'],folder/'deck.pptx')
    for name in ('spec','brief','ledger'):shutil.copy2(ACCEPT/f'{r["case"]}-{name}.json',folder/f'{name}.json')
    mp=ACCEPT/r['case']/('render-manifest.json' if r['case']=='existing-ppt-edit' else 'rev-000/qa-000/render-manifest.json')
    manifest=read(mp);shutil.copy2(mp,folder/'render-manifest.json')
    for image in manifest['images']:shutil.copy2(image['path'],folder/Path(image['path']).name)
    if r['case']!='existing-ppt-edit':shutil.copytree(mp.parent,folder/'qa')
    else:shutil.copy2(mp.parent/'native-inspection.json',folder/'native-inspection.json')
    visual.append({'case':r['case'],'deck_sha256':r['sha256'],'spec_sha256':sha(ACCEPT/f'{r["case"]}-spec.json'),
        'render_manifest_sha256':sha(mp),'images':manifest['images']})
shutil.copytree(ACCEPT/'previews',OUT/'预览')
shutil.copytree(ROOT/'runs/p5-licenses-002',OUT/'licenses')
proof=OUT/'验证记录';proof.mkdir()
shutil.copytree(REPRO,proof/'最终ZIP复现')
shutil.copytree(TESTED/'runs/p5-cli-smoke',proof/'CLI与安装',ignore=shutil.ignore_patterns('installed','handoffs'))
for name in ('p5-final-regression-tests.log','p5-global-installation.json','p5-skill-validation.json'):
    shutil.copy2(ROOT/'runs'/name,proof/name)
for name in ('p5-clean-contract-tests.log','p5-clean-qa-tests.log','p5-clean-qa-tests-v2.log','p5-clean-render-tests.log','p5-clean-chart-tests.log'):
    shutil.copy2(TESTED/'runs'/name,proof/name)
shutil.copy2(TESTED/'installation.json',proof/'首次离线安装.json')
finalroot=ROOT/'runs/p5-reinstall-004/ppt-workflow'
shutil.copy2(finalroot/'installation.json',proof/'最终ZIP离线安装.json')
shutil.copy2(finalroot/'runs/portable-smoke.json',proof/'最终ZIP-77项测试.json')
for name in ('runtime-install-report.json','office-install-report.json'):
    shutil.copy2(finalroot/name,proof/name)
shutil.copy2(ACCEPT/'results.json',OUT/'任务实测.json');shutil.copy2(ACCEPT/'frozen-evaluation.json',proof/'留出探针冻结.json')
scripts=OUT/'验收脚本';scripts.mkdir()
for p in (ROOT/'scripts').glob('*p5*.py'):shutil.copy2(p,scripts/p.name)
for name in ('使用指南.md','THIRD_PARTY_NOTICES.md'):shutil.copy2(ROOT/name,OUT/name)
shutil.copy2(ROOT/'docs/任务验收矩阵.md',OUT/'任务验收矩阵.md')
save(OUT/'视觉观察.json',{'scope':'Supplemental host review, not a production visual approval record',
    'contact_sheets_viewed':['academic','business','mixed-technical','table-series','existing-ppt-edit'],
    'full_size_pages_viewed':{'academic':[1,5,10],'mixed-technical':[1,2,5,8],'table-series':[1,8],'existing-ppt-edit':[3,5,8]},
    'observations':[
      '暖白底、青绿主色、微软雅黑与页眉页脚保持一致；中英标题完整，未见明显溢出。',
      '84与7的图表比例正确、标签在绘图区内，差值77和耗时比12在指标与表格同步；轴上限已由固定46改为97。',
      '36/2/34/18现有PPT修改稿同步更新原生图表缓存、工作簿和表格；插画仍是位图。',
      '8页表格系列结构一致且保留三列不等宽；它是功能探针，不是设计多样性或自动长表分页证据。',
      '答辩探针沿用示意业务内容，仅检查中文主张标题重排，不能算真实论文答辩验收。'],
    'decision':'No obvious blockers in viewed pages; comprehensive per-page production visual approval not claimed',
    'bindings':visual,'quality_unknowns_retained':True})
save(OUT/'verification.json',{'stage':'P5','status':'candidate-delivery-prepared-awaiting-human-review',
    'source_regression':207,'portable_tests':77,'portable_skips':0,'skill_folders_installed':7,
    'stage_routes_verified':6,'fresh_installations':2,'same_physical_host':True,'other_machine_or_clean_OS':False,
    'task_types_planned':6,'synthetic_mechanical_cases_passed':5,'blocked_missing_brand_template':1,
    'rendered_task_pages':48,'final_ZIP_smoke_pages':10,'unverified_delivery_denied':5,
    'historical_files_checked':54,'historical_files_changed':changed,
    'release_status':'unverified-not-public-release','quality_unknown_counts':{r['case']:r.get('unknown') for r in rows if r['status']=='mechanically-passed'},
    'licensing_open_items':['https1.0.0 declared ISC but license text not obtained','project public release license not assigned'],
    'P4_external_framework_comparison':'still-not-completed','Figma_to_PPTX_roundtrip':'still-not-verified',
    'candidate_package':read(OUT/'candidate-package.json')})
task_table='\n'.join(f'| {r["case"]} | {r.get("pages","—")} | {r["status"]} | {r.get("unknown","—")} |' for r in rows)
report=f'''# P5 安装与交付固化：候选版审核

日期：2026-10-16。结论：本地候选工作流、安装包与使用文档已准备并验证，等待G5用户审核。六类任务中真实品牌模板尚无材料，完整质量门槛未满足；本报告不宣布正式release或六类任务全部通过。

## 本轮交付

六个独立Skill和总控已安装到个人Codex技能目录，runtime.json指向当前项目。七个源文件包通过skill-creator校验，安装后逐文件比对通过；既有技能与配置未覆盖。新会话或刷新技能列表后，可用 `$ppt-quality-workflow` 启动整套流程，也可单独调用 `$ppt-intake`、`$ppt-outline`、`$ppt-template`、`$ppt-compose`、`$ppt-polish`、`$ppt-review`。

终端intake/outline/template/compose/polish/review分别路由到独立Skill。宿主读取相应Skill执行实际专业工作；CLI负责文件交接、依赖和批准校验，不会自动执行语言模型。干净环境验证了6条路由、7个本地安装副本及重复安装拒绝；没有创建假用户审批。

《PPT工作流-候选安装包-v0.1.zip》包含完整主线运行代码、七个Skill、真实POTX、统一设计规范、概念图与提示词、依赖锁、35个Python wheel、19个Node tarball、77项可迁移测试、许可记录、bootstrap和使用指南。包不带Python/Node/Office/商业字体二进制，不带全部历史研究run，也没有默认集成P4的隔离automizer实验。包内225个清单文件均经解压哈希核对。

## 两次独立目录安装

第一次在p5-dist-003创建全新.venv、.mcp-venv及node_modules，固定依赖离线安装成功，耗时52.455秒。第二次从最终ZIP解压到不同的p5-reinstall-004目录，再创建全新环境，安装耗时35.268秒；77项测试无失败、无跳过，通过真实MCP→PowerPoint生成和渲染10页演示，质量门禁正确拒绝其正式交付。

这验证了同一台Windows机器上的目录迁移与依赖重建，不是干净操作系统或第二台机器测试。前提为Windows x64、Python3.12、Node、PowerPoint与本机字体。详见《使用指南.md》。下载仅发生在备包时，bootstrap使用固定hash的本地依赖，不依赖网络安装或旧node_modules。

## 实现改动与发现

图表生成器原先固定轴上限46。本轮改为非负数据最大值的1.15倍向上取整，最小上限1；40/1基线仍为46，60/4和全零用例新增回归；不支持的负数明确拒绝。冻结生成器和检查器后，用84/7/77/12混排探针验证，PowerPoint中轴上限97，原生缓存、工作簿与可见图表一致。它只是同一模板的数据/文字留出样例，不证明其他模板泛化。

新增离线安装器，拒绝覆盖已有环境，校验依赖hash，安装脚本关闭，两个Python环境分别pip check。增加hash损坏拒绝、预览不创建环境、已有环境保留等测试。完整原项目207项回归通过；包内可迁移子集77项均通过，不能将子集冒充全部集成质量检查。

打包时Windows长路径导致原npm缓存复制失败，已改为可核对integrity的短文件名tarball。首次受限venv的ensurepip失败目录保留，正式两次安装另起新目录。干净QA初次有两项依赖历史夹具而失败，现将五个原夹具以同hash副本纳入tests/fixtures，复测36/36通过。表格探针最初误声明必须含图表，被合同门禁拒绝；修正该任务需求为文字及表格后通过，未放宽门禁。

个人技能目录安装的首次自动权限审核超时未执行，按工具允许重试一次后成功；这不是安全否决，最终七目录实测存在且内容匹配。详见验证记录。

## 六类任务实测

各任务均为明确示意材料，只有原生对象/事实绑定及渲染的机械范围通过，不能当作真实业务内容审批。四个主线任务均零报告error，但综合QA仍unverified；现有PPT修改使用P4隔离辅助脚本，不算主包已集成。

| 任务 | 页数 | 机械执行状态 | 主线unknown数 |
|---|---:|---|---:|
{task_table}

任务共48页真实PowerPoint渲染；另有最终ZIP安装演示10页。主线四份候选和最终ZIP演示的deliver均被正确拒绝，总计5次；没有创建正式交付目录。表格系列124项unknown主要随单元格样式继承数量增加，不能与普通稿20项合并成平均分掩盖。

已查看五份接触表及记录中的全尺寸重点页。补充观察没有发现明显裁切或数值错位；并未声称完成48页全尺寸独立视觉签字，也未把观察写回生产QA以清除unknown。完整逐页图像随审核包提供。

## 仍未完成

完整OOXML schema、交互编辑保存往返及部分表格/文字测量仍未验证。真实学院/品牌模板、多表同页/长表自动分页、复杂图表、WPS、Figma→PPTX可编辑往返均未通过验收。P4两个独立外部生成框架的对照也没有补齐。图像仍是位图；本轮没有把生图模型名称或插件连接假定为固定能力。

许可证与来源按实际包收录。isarray的MIT原文位于README，已保留；https1.0.0仅取得ISC元数据声明，没有独立许可正文。自有源码尚未指定公开发布许可证。当前ZIP是给用户的本地候选，不作为公开发行许可已清的声明。

54个历史原文件hash保持不变。新生成器会使旧构建任务的输入绑定失效；旧PPT和审核包保留，变更后请新建plan，不修改旧记录冒充resume。

## G5审核内容

请审核七个Skill的职责与调用方式、使用指南、样例效果及候选安装包，决定是否接受当前边界作为本地试用版。G5的用户确认也不会自动清除质量unknown、补齐真实品牌材料或改变公开发布许可；正式release仍须分别满足这些条件。

主运行时：[当前项目](../../ppt-workflow/README.md)。使用方法见《使用指南.md》；清单见verification.json；原生样例与48页PNG见“样例”，接触表见“预览”，安装/测试/门禁日志见“验证记录”。审核材料中的绝对路径仍指向本项目；候选安装ZIP已在不同目录真实复现。
'''
(OUT/'P5阶段审核.md').write_text(report,encoding='utf-8')
statefile=PROJECT/'06-实施与阶段审核/阶段状态.json';state=read(statefile)
state['stages']['P5'].update(implementation='candidate_completed_with_limitations',review='awaiting_user',report='P5-交付固化/P5阶段审核.md',
    skill_installation='seven-personal-skills-installed-and-verified',formal_release='unverified-not-published',
    verification='207 source regression +77 portable tests; two fresh-path offline installs; five synthetic mechanical task probes; one real-brand task blocked',
    outstanding=['真实品牌模板未提供','完整质量unknown仍保留','独立外部生成框架对照未完成','公开发布许可未定及https许可正文未取得'])
save(statefile,state)
manifest=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file()]
save(OUT/'manifest.json',manifest)
archive=OUT.parent/'P5-交付固化审核包.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(OUT))
with ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'review':str(OUT),'files':len(manifest),'audit_zip_bytes':archive.stat().st_size,'audit_zip_sha256':sha(archive)},ensure_ascii=False))
