from pathlib import Path
from zipfile import ZipFile
import json,hashlib,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
OUT=PROJECT/'06-实施与阶段审核/最终整理-20261017'
CHECK=ROOT/'runs/final-connections-20261017-003'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
verification=read(CHECK/'verification.json');assert verification['status']=='passed-for-documented-local-path'
full=(ROOT/'runs/final-maintenance-tests-passed-20261017.log').read_text(encoding='utf-8')
portable=(ROOT/'runs/final-portable-tests-20261017.log').read_text(encoding='utf-8')
assert 'Ran 210 tests' in full and full.rstrip().endswith('OK')
assert 'Ran 80 tests' in portable and portable.rstrip().endswith('OK')
first=read(OUT/'清理结果.json');empty=read(OUT/'清理结果-空目录.json')
clean={r['path']:r for r in first['records']}
clean.update({r['path']:r for r in empty['records']})
assert all(r['status']=='deleted' and not Path(r['path']).exists() for r in clean.values())
cleanup={'deleted_directories':len(clean),'deleted_bytes':first['deleted_bytes']+(empty.get('deleted_bytes') or 0),
    'MiB':round((first['deleted_bytes']+(empty.get('deleted_bytes') or 0))/1048576,2),
    'empty_directory_followup':len(empty['records']),'details':list(clean.values())}
save(OUT/'清理汇总.json',cleanup)
baseline=read(PROJECT/'06-实施与阶段审核/P0/baseline-manifest.json')
changed=[r['path'] for r in baseline['originals'] if sha(PROJECT/r['path'])!=r['sha256']];assert not changed
names=['ppt-quality-workflow']+[s['skill'] for s in read(ROOT/'skill-routing.json')['stages']]
skills=[];validator=Path.home()/'.codex/skills/.system/skill-creator/scripts/quick_validate.py'
for name in names:
    source=ROOT/'skills'/name;installed=Path.home()/'.codex/skills'/name
    binding=read(installed/'runtime.json');assert Path(binding['project_root']).resolve()==ROOT
    matches=all(sha(f)==sha(installed/f.relative_to(source)) for f in source.rglob('*') if f.is_file() and f.name!='runtime.json')
    assert matches
    p=subprocess.run(['D:/Python/python.exe','-X','utf8',str(validator),str(installed)],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert p.returncode==0,p.stderr
    skills.append({'skill':name,'installed':str(installed),'matches_source':matches,'validation':p.stdout.strip()})
save(OUT/'技能与路径核查.json',skills)
archive=OUT/'PPT工作流-整理版-20261017.zip'
with ZipFile(archive) as z:
    m=json.loads(z.read('manifest.json'))
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'] for r in m)
    for path in ['scripts/office_mcp_client.py','office-mcp/server.py','scripts/smoke.py','README.md','docs/工具与连接.md']:
        assert z.read('ppt-workflow/'+path)==(ROOT/path).read_bytes()
legacy_render=read(PROJECT/'06-实施与阶段审核/P5-交付固化/样例/business/render-manifest.json')
current_render=read(CHECK/'job/rev-000/qa-000/render-manifest.json')
visual_equivalence=[r['sha256'] for r in legacy_render['images']]==[r['sha256'] for r in current_render['images']]
proof=OUT/'主线记录';proof.mkdir(exist_ok=False)
for name in ('commands.json','verification.json'):
    (proof/name).write_bytes((CHECK/name).read_bytes())
for relative in ('health/mcp-client.json','catalog/office-worker.json','template/office-worker.json','instantiated/office-worker.json','job/rev-000/qa-000/qa.json','job/rev-000/qa-000/render-manifest.json'):
    target=proof/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((CHECK/relative).read_bytes())
for name in ('final-maintenance-tests-20261017.log','final-client-tests-20261017.log','final-client-tests-fixed-20261017.log','final-maintenance-tests-passed-20261017.log','final-portable-tests-20261017.log'):
    (OUT/name).write_bytes((ROOT/'runs'/name).read_bytes())
save(OUT/'verification.json',{'date':'2026-10-17','status':'documented-local-workflow-verified',
    'mcp_operations_passed':5,'routes_passed':6,'source_tests':210,'portable_tests':80,'test_skips':0,
    'installed_skills':7,'rendered_pages':10,'render_pixels_match_previously_reviewed_business_deck':visual_equivalence,
    'cleanup_directories':cleanup['deleted_directories'],'cleanup_bytes':cleanup['deleted_bytes'],
    'historical_originals':len(baseline['originals']),'historical_changes':changed,'quality_unknown':verification['quality_unknown'],
    'figma':'authentication-and-existing-file-read-passed; write/export-not-exercised',
    'online_powerpoint':'no-active-session; optional','image_generation':'tool-present-not-invoked; fixed-model-id-not-exposed',
    'package_files_verified':len(m),'package_sha256':sha(archive),'formal_release':'quality-unverified-no-public-release'})
report=f'''# PPT 工作流最终整理与核查

日期：2026-10-17。当前主线可用性检查通过；不能据此承诺所有外部服务、模型或未来任务永远无问题。当前入口为项目根“当前工作流.md”，源码与运行环境在ppt-workflow，七个个人Skill副本均已同步并核对。

## 结果

| 项目 | 本次验证 | 结论 |
|---|---|---|
| 六阶段及总控 | 7个安装副本、runtime路径、内容比对与skill-creator校验 | 通过；职责保持解耦 |
| 六阶段命令 | 缺交接时返回路由或明确阻止，不伪造批准 | 6/6符合预期 |
| 本地Office MCP | 实际stdio握手、工具schema与5种operation调用 | 5/5通过 |
| PowerPoint原生能力 | 新模板、从POTX创建、制作、10页1600×900渲染；4个独占worker均正确清理 | 通过 |
| 正式交付门禁 | 当前QA仍有{verification['quality_unknown']}项unknown，deliver拒绝放行 | 符合预期，没有降低门槛 |
| 完整回归/可迁移子集 | 最终210项/80项，无失败、无跳过 | 通过；子集不是全部质量验收 |
| Figma | 当前认证与现有Slides文件只读查询 | 通过读取；写入/导出往返未验证 |
| 在线PowerPoint | Document Control列出会话为空 | 未连接；不影响本地主线 |
| 生图 | 宿主工具存在、既有图片可用；没有为自检创建新资产 | 未执行新生图，不声称固定Image2接口已实测 |
| 文档链接 | 四个官方说明页面可访问；旧OpenAI地址重定向至当前页面 | 已登记当前落点 |

本次10页渲染与P5已审商务示意稿的逐页像素哈希一致：{visual_equivalence}。这证明本轮维护没有改变该样例的可见内容，并不扩大其他模板的设计或质量覆盖。

## 已修正

1. 制作Skill移除对历史运行目录的默认调用，改为create_demo生成本机绑定的示意输入；正式任务仍走已批准的内容与模板。
2. 明确本地MCP是stdio服务，没有虚构HTTP URL或API key；增加health_check并保存真实工具schema。
3. 更正SmartArt能力说明，统一主线采用原生组合形状；校对Figma Slides、在线文档会话和生图工具的实际使用条件。
4. MCP客户端增加清晰的参数检查、输入边界与已有输出拒绝，避免覆盖旧证据。首次参数测试在受限环境超时，延后SDK加载后仍超时；最终将参数校验移到异步事件循环创建之前，三项保护检查0.579秒通过。失败日志与最终成功日志都保留，不删除失败伪装一次通过。
5. 修复P2原生测试临时目录不自动回收的问题，新增已确认目录内的清理；当前测试不再不断堆积这类目录。
6. 当前README、使用指南、连接说明和脚本索引统一日常入口。旧P0–P5包原样保留；新版整理包另存，未改写旧批准件。

## 清理

已删除{cleanup['deleted_directories']}个确认可丢弃的目录，清单计{cleanup['deleted_bytes']:,}字节（{cleanup['MiB']} MiB），主要为重复安装环境、失败安装副本、下载缓存和临时测试变体。第一轮因PowerShell空目录Sum返回null而跳过71个空测试目录；按原清单再次确认全为空后清除，记录分别保留。实际空间释放按删除前文件长度统计，非磁盘空闲块测量。

保留主.venv/.mcp-venv/node_modules、隔离automizer、模板素材、实际PPT及PNG、校准夹具、成功运行日志、P0–P5审核ZIP和全部54个历史原文件。原文件hash无变化。已清理的重复环境不再可直接resume；历史代码/审核输入变更本来也需新建plan。当前环境与新目录实测不依赖这些被清目录。

## 当前安装包

PPT工作流-整理版-20261017.zip含当前代码、七个Skill、模板素材、同锁离线依赖、连接验证入口与80项可迁移测试。{len(m)}个文件清单逐项hash核对通过。包内关键客户端、服务、测试入口和文档与实测源码相同。

依赖与bootstrap未变，沿用P5同一物理主机上两次全新路径离线安装的证据；本轮没有再做一次完整解压安装，也不是第二台机器或干净操作系统验收。新版原样保留许可记录及公开分发前待核事项，不将本地试用维护解释为公开发布许可已清。

## 仍需按条件使用

Figma外部认证会变化，文件可读不等于可写；在线PowerPoint当前没有活跃会话；WPS没有验证通路。生图的实际工具和可选模型以执行时宿主提供的信息为准。完整OOXML校验、交互编辑回存、部分文字/表格继承及Figma→PPTX往返仍未验证。外部框架对照与真实品牌模板仍按原报告列为未完成，不能写成“所有能力均无问题”。

连接入口与官方链接见ppt-workflow/docs/工具与连接.md，详细证据见本目录JSON、日志、技能更新前备份与清理清单。当前主线将缺连接/不支持情况明确报告，避免在任务中调用不存在的服务或静默换路径。
'''
(OUT/'最终核查报告.md').write_text(report,encoding='utf-8')
paths=[PROJECT/'当前工作流.md',ROOT/'README.md',ROOT/'使用指南.md',*(ROOT/'docs').glob('*.md'),*(ROOT/'skills').rglob('*.md')]
paths += [p for name in names for p in (Path.home()/'.codex/skills'/name).rglob('*.md')]
broken=[]
for path in paths:
    text=re.sub(r'```.*?```','',path.read_text(encoding='utf-8-sig'),flags=re.S)
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
        if target.startswith(('https://','http://','#','app://')):continue
        target=target.strip('<>').split('#')[0]
        if target and not (path.parent/target).resolve().exists():broken.append({'file':str(path),'target':target})
assert not broken,broken
save(OUT/'本地链接核查.json',{'markdown_files':len(paths),'broken_links':broken})
statefile=PROJECT/'06-实施与阶段审核/阶段状态.json';state=read(statefile)
state['last_maintenance']={'date':'2026-10-17','authorization':'用户要求最终整理、核对工具/MCP/接口链接并清理无用文件',
    'status':'verified-with-documented-external-conditions','report':'最终整理-20261017/最终核查报告.md',
    'source_tests':210,'portable_tests':80,'installed_skills':7,'cleanup_bytes':cleanup['deleted_bytes'],'quality_gate_unchanged':True}
save(statefile,state)
manifest=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file()]
save(OUT/'manifest.json',manifest)
print(json.dumps({'report':str(OUT/'最终核查报告.md'),'files':len(manifest),'broken_links':len(broken),'deleted_MiB':cleanup['MiB'],'source_tests':210,'portable_tests':80},ensure_ascii=False))
