"""Publish role-based themes from the existing palette family for native recipes."""
from copy import deepcopy
from .design import THEMES
from .online_assets import ROOT, fresh, read, write, sha

PROFILES = {
    'research-light': dict(palette='academic', name='明亮研究', secondary='91B5B8',
        use='教室、会议室、研究资料汇报及打印阅读',
        imagery='暖白或自然光照片、青绿材质插画；必要时使用清晰独立图幅',
        tone='白底、深色正文、青绿重点；以留白和字号建立层级'),
    'showcase-dark': dict(palette='technical', name='深色展示', secondary='526F83',
        use='可控光线中的短展示、技术方案与大屏汇报',
        imagery='深蓝青绿场景优先；明亮图片保留为独立矩形图幅，不强行抠图或染色',
        tone='深蓝底、浅色文字、薄荷青重点；图表轴与来源均使用浅色角色'),
}
LAYOUTS = ['cover','divider','closing','text-wide','text-columns','image-led',
           'image-balanced','image-right','image-story','image-chart',
           'process','hierarchy','comparison','chart_takeaway']

def theme_bundle(theme_id):
    if theme_id not in PROFILES: raise ValueError('Unknown theme ID')
    profile=PROFILES[theme_id];p=THEMES[profile['palette']]
    colors=dict(background=p['bg'],ink=p['ink'],accent=p['accent'],muted=p['muted'],
                surface=p['light'],line=p['rule'],secondary=profile['secondary'])
    design=dict(id=theme_id,font=p['font'],colors=colors,
                layouts=[dict(key=k,name=k) for k in LAYOUTS])
    style=dict(version='visual-style/1',id=theme_id,medium='mixed',colors=deepcopy(colors),
               material=profile['imagery'],line='原生文字、直线和实色；图表保留事实与零基线',
               tone=profile['tone'],references=[])
    return dict(design_system=design,asset_style=style,selection=deepcopy(profile))

def theme_catalog():
    previews=ROOT/'templates/theme-families/previews.json'
    saved=read(previews) if previews.is_file() else {}
    rows=[]
    for key,profile in PROFILES.items():
        row=dict(id=key,**deepcopy(profile),colors=theme_bundle(key)['design_system']['colors'],previews=[])
        for item in saved.get(key,[]):
            path=(ROOT/item['path']).resolve()
            if not path.is_relative_to(ROOT/'templates/theme-families') or sha(path.read_bytes())!=item['sha256']:
                raise ValueError('Theme preview changed')
            row['previews'].append(str(path))
        rows.append(row)
    return dict(themes=rows,scope='Owned widescreen recipe themes; not arbitrary Office/WPS template imports',
                approval='Representative pages require user review')

def prepare_theme(theme_id,out):
    bundle=theme_bundle(theme_id);out=fresh(out);out.mkdir(parents=True)
    write(out/'design-system.json',bundle['design_system']);write(out/'asset-style.json',bundle['asset_style'])
    write(out/'selection-guidance.json',bundle['selection'])
    return dict(status='prepared',theme_id=theme_id,design_system=str(out/'design-system.json'),
                asset_style=str(out/'asset-style.json'),approval='not_implied')
