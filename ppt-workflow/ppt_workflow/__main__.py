"""python -m ppt_workflow <command>; JSON output and meaningful exit codes."""
import argparse
import json
from pathlib import Path
import sys

from . import workflow as w
from . import stages


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ppt_workflow")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("skills")
    sub.add_parser('capabilities')
    sub.add_parser('template-catalog')
    sub.add_parser('chart-style-catalog')
    sub.add_parser('frame-catalog')
    sub.add_parser('theme-catalog')
    p=sub.add_parser('theme-prepare');p.add_argument('--theme',required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('chart-prepare');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('module-search');p.add_argument('--query',default='')
    p=sub.add_parser('module-prepare');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('relationship-prepare');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    for name in ('layout-plan','page-prepare'):
        p=sub.add_parser(name);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    for name in ('asset-plan','asset-record','trend-prepare','frame-prepare','compact-chart-prepare'):
        p=sub.add_parser(name);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('brief-compose');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--node',type=Path,required=True)
    p=sub.add_parser('asset-search');p.add_argument('--query',default='');p.add_argument('--use');p.add_argument('--style');p.add_argument('--min-width',type=int,default=1);p.add_argument('--limit',type=int,default=8);p.add_argument('--out',type=Path);p.add_argument('--type',choices=['image','icon','illustration','all'],default='image');p.add_argument('--category')
    p=sub.add_parser('asset-prepare');p.add_argument('--asset-id',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--color');p.add_argument('--size',type=int);p.add_argument('--slide-id',required=True);p.add_argument('--element-id',required=True);p.add_argument('--reason',required=True)
    p=sub.add_parser('asset-discover');p.add_argument('--query',required=True);p.add_argument('--provider',choices=['all','iconify','openverse','commons','cache'],default='all');p.add_argument('--keywords');p.add_argument('--orientation',choices=['any','landscape','portrait','square'],default='any');p.add_argument('--min-width',type=int,default=0);p.add_argument('--page',type=int,default=1);p.add_argument('--limit',type=int,default=8);p.add_argument('--offline',action='store_true');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('asset-fetch');p.add_argument('--results',type=Path,required=True);p.add_argument('--asset-id',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--color',default='162E3B');p.add_argument('--node',type=Path);p.add_argument('--sharp',type=Path);p.add_argument('--offline',action='store_true')
    p=sub.add_parser('editorial-build');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--design',type=Path)
    p=sub.add_parser('material-pack');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('asset-place');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('blueprint-build');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--node',type=Path,required=True)
    p=sub.add_parser('quality-check');p.add_argument('--outline',type=Path,required=True);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--requirements',type=Path);p.add_argument('--out',type=Path,required=True)
    for entry in stages.registry()['stages']:
        p = sub.add_parser(entry['command'])
        p.add_argument('--workspace', type=Path, required=True)
        p.add_argument('--input', type=Path)
        p.add_argument('--approve', help='Exact artifact SHA256; never implicit approval')
        p.add_argument('--reviewer')
        p.add_argument('--evidence')
    sub.add_parser("doctor")
    p = sub.add_parser("plan"); p.add_argument("--config", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("build"); p.add_argument("--run", type=Path, required=True); p.add_argument("--resume", action="store_true"); p.add_argument("--with-qa", action="store_true"); p.add_argument("--retry-environment", action="store_true")
    p = sub.add_parser("qa"); p.add_argument("--run", type=Path, required=True); p.add_argument("--review", type=Path); p.add_argument("--retry-environment", action="store_true"); p.add_argument("--reserve-visual-call", action="store_true")
    p = sub.add_parser("revise"); p.add_argument("--run", type=Path, required=True); p.add_argument("--patch", type=Path, required=True)
    p = sub.add_parser("deliver"); p.add_argument("--run", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("benchmark"); p.add_argument("--runs", type=Path, nargs="+", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command=='asset-discover':
            from .online_assets import discover
            result=discover(args.query,args.out,provider=args.provider,keywords=args.keywords,page=args.page,limit=args.limit,offline=args.offline,orientation=args.orientation,min_width=args.min_width)
        elif args.command=='asset-fetch':
            from .online_assets import fetch
            result=fetch(args.results,args.asset_id,args.out,color=args.color,node=args.node,sharp=args.sharp,offline=args.offline)
        elif args.command=='editorial-build':
            from .editorial_builder import build_editorial
            result=build_editorial(args.input,args.out,args.node,args.design)
        elif args.command=='material-pack':
            from .production_materials import build_pack
            result=build_pack(args.input,args.out)
        elif args.command=='asset-place':
            from .asset_placement import place
            result=place(args.input,args.out)
        elif args.command=='asset-search':
            from .asset_library import search_assets,write_gallery
            result=search_assets(args.query,use=args.use,style=args.style,min_width=args.min_width,limit=args.limit,asset_type=args.type,category=args.category)
            if args.out:result['gallery']=write_gallery(result,args.out)
        elif args.command=='asset-prepare':
            if args.asset_id.startswith('peeps:'):
                from .illustration_library import prepare_illustration
                result=prepare_illustration(args.asset_id,args.out,color=args.color,size=args.size if args.size is not None else 1024,slide_id=args.slide_id,element_id=args.element_id,reason=args.reason)
            else:
                from .icon_library import prepare_icon
                result=prepare_icon(args.asset_id,args.out,color=args.color if args.color is not None else '162E3B',size=args.size if args.size is not None else 256,slide_id=args.slide_id,element_id=args.element_id,reason=args.reason)
        elif args.command=='chart-style-catalog':
            from .chart_style_library import style_catalog
            result=style_catalog()
        elif args.command=='chart-prepare':
            from .chart_style_library import prepare_chart_style
            result=prepare_chart_style(args.input,args.out)
        elif args.command=='module-search':
            from .module_library import search_modules
            result=search_modules(args.query)
        elif args.command=='module-prepare':
            from .module_library import prepare_module
            result=prepare_module(args.input,args.out)
        elif args.command=='theme-catalog':
            from .theme_library import theme_catalog
            result=theme_catalog()
        elif args.command=='theme-prepare':
            from .theme_library import prepare_theme
            result=prepare_theme(args.theme,args.out)
        elif args.command=='compact-chart-prepare':
            from .paired_evidence import prepare_compact_chart
            result=prepare_compact_chart(args.input,args.out)
        elif args.command=='frame-catalog':
            from .editorial_frames import frame_catalog
            result=frame_catalog()
        elif args.command=='frame-prepare':
            from .editorial_frames import prepare_frame
            result=prepare_frame(args.input,args.out)
        elif args.command=='brief-compose':
            from .brief_composer import compose_brief
            result=compose_brief(args.input,args.out,args.node)
        elif args.command in ('asset-plan','asset-record'):
            from .asset_direction import plan_assets,record_asset
            result=(plan_assets if args.command=='asset-plan' else record_asset)(args.input,args.out)
        elif args.command=='trend-prepare':
            from .trend_annotations import prepare_trend
            result=prepare_trend(args.input,args.out)
        elif args.command in ('layout-plan','page-prepare'):
            from .layout_capacity import prepare_layout
            result=prepare_layout(args.input,args.out,compose=args.command=='page-prepare')
        elif args.command=='relationship-prepare':
            from .relationships import prepare_relationship
            result=prepare_relationship(args.input,args.out)
        elif args.command=='template-catalog':
            from .blueprints import catalog
            from .layout_capacity import capacity_catalog
            from .theme_library import theme_catalog
            result={'status':'available','templates':catalog(),'capacity_templates':capacity_catalog(),'theme_families':theme_catalog()['themes'],'visual_approval':'not_implied'}
        elif args.command=='blueprint-build':
            from .blueprints import build_blueprint
            result=build_blueprint(args.input,args.out,args.node)
        elif args.command=='capabilities':
            from .charts import capabilities
            result={'status':'available','schema_versions':['0.1','0.2'],**capabilities()}
        elif args.command=='quality-check':
            from .quality import validate_content_plan,review_scaffold
            plan_path,outline_path=w.local(args.plan),w.local(args.outline)
            plan,outline=w.read(plan_path),w.read(outline_path)
            requirements=w.read(w.local(args.requirements)) if args.requirements else None
            errors=validate_content_plan(plan,outline,requirements)
            if 'outline_sha256' in plan and plan['outline_sha256']!=w.sha256(outline_path):errors.append('Outline bytes changed')
            if 'baseline' in plan:
                if w.sha256(w.local(plan['baseline']['path'],plan_path.parent))!=plan['baseline']['sha256']:errors.append('Baseline bytes changed')
            out=w.fresh_run(args.out);out.mkdir(parents=True,exist_ok=False)
            result={'status':'failed' if errors else 'needs_review','errors':errors,'automated_checks_passed':not errors,
                    'human_semantic_review':'not_performed_by_cli','human_visual_review':'not_performed_by_cli','release_allowed':False,
                    'plan_sha256':w.sha256(plan_path),'outline_sha256':w.sha256(outline_path)}
            w.write(out/'quality-check.json',result)
            if not errors:w.write(out/'quality-review-draft.json',review_scaffold(plan))
        elif args.command == 'skills':
            result = {'stages': [{**s, 'route': stages.skill_route(s['command'])} for s in stages.registry()['stages']],
                      'utilities': {k: stages.skill_route(k) for k in stages.registry()['utilities']}}
        elif args.command in {s['command'] for s in stages.registry()['stages']}:
            result = stages.stage_action(args.command, args.workspace, input_path=args.input, approve=args.approve,
                                         reviewer=args.reviewer, evidence=args.evidence)
        elif args.command == "doctor": result = w.doctor()
        elif args.command == "plan": result = w.plan(args.config, args.out)
        elif args.command == "build":
            result = w.build(args.run, resume=args.resume, retry_environment=args.retry_environment)
            if args.with_qa: result = w.qa(args.run)
        elif args.command == "qa":
            if args.reserve_visual_call and (args.review or args.retry_environment):
                raise ValueError("Visual reservation is separate from review attachment and environment retries")
            result = w.reserve_visual_call(args.run) if args.reserve_visual_call else w.qa(args.run, review_path=args.review, retry_environment=args.retry_environment)
        elif args.command == "revise": result = w.revise(args.run, args.patch)
        elif args.command == "deliver": result = w.deliver(args.run, args.out)
        else: result = w.benchmark(args.runs)
        result['skill_route'] = stages.skill_route(args.command)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") in {"failed", "blocked"} else 2 if result.get("status") in {"needs_review", "unverified", "needs_input", "needs_skill_execution", "partial"} else 0
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
