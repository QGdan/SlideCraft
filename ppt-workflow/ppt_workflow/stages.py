"""Six skill-owned stages; CLI validates handoffs, the host executes the skill."""
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
from defusedxml import ElementTree as ET
from pptx import Presentation

from .contracts import validate
from .content import check_ledger, inspect_native
from .workflow import ROOT, WorkflowError, read, write, sha256, digest, fresh_run, locked

PROJECT = ROOT.parent
REGISTRY = ROOT / 'skill-routing.json'


def registry():
    return read(REGISTRY)


def skill_route(command):
    stage = next((s for s in registry()['stages'] if s['command'] == command), None)
    name = stage['skill'] if stage else registry()['utilities'][command]
    path = ROOT / 'skills' / name / 'SKILL.md'
    if not path.is_file():
        raise WorkflowError(f'Skill is unavailable: {name}')
    return {'skill': name, 'path': str(path), 'host_must_load_skill': True,
            'cli_invokes_language_model': False}


def _skill_digest(stage):
    folder = Path(skill_route(stage)['path']).parent
    return digest([{'path':str(p.relative_to(folder)),'sha256':sha256(p)} for p in sorted(folder.rglob('*'))
                   if p.is_file() and p.suffix in ('.md','.json','.yaml','.py')])


def _rules_digest():
    paths=[Path(__file__),ROOT/'ppt_workflow/contracts.py',ROOT/'ppt_workflow/quality.py',ROOT/'ppt_workflow/charts.py',ROOT/'ppt_workflow/content.py',ROOT/'engine/capabilities.json']
    paths.extend(sorted((ROOT/'schemas').glob('*.json')))
    paths.append(ROOT/'ppt_workflow/blueprints.py')
    paths.extend([ROOT/'ppt_workflow/exhibits.py',ROOT/'ppt_workflow/asset_library.py',ROOT/'ppt_workflow/icon_library.py'])
    paths.extend([ROOT/'scripts/render_direct.ps1',ROOT/'scripts/verify_direct_render.py'])
    paths.extend([ROOT/'ppt_workflow/illustration_library.py',ROOT/'ppt_workflow/module_library.py',ROOT/'templates/modules/library.json'])
    paths.extend([ROOT/'ppt_workflow/chart_style_library.py',ROOT/'templates/chart-styles/library.json'])
    paths.extend([ROOT/'ppt_workflow/chart_preservation.py',ROOT/'ppt_workflow/wps_bridge.py'])
    paths.extend([ROOT/'ppt_workflow/online_assets.py',ROOT/'ppt_workflow/asset_placement.py'])
    paths.append(ROOT/'ppt_workflow/production_materials.py')
    paths.extend([ROOT/'ppt_workflow/editorial.py',ROOT/'ppt_workflow/editorial_builder.py',ROOT/'ppt_workflow/export_fix.py'])
    paths.extend(sorted((ROOT/'engine').glob('*.cjs')))
    paths.extend(sorted((ROOT/'templates').glob('*/blueprint.json')))
    return digest([{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in paths])


def _path(value, base):
    path = (Path(base) / value).resolve()
    if not path.is_relative_to(PROJECT) or not path.is_file():
        raise WorkflowError(f'Existing workspace-local artifact required: {value}')
    return path


def _text(payload, *keys):
    if any(not isinstance(payload.get(k), str) or not payload[k].strip() for k in keys):
        raise WorkflowError('Required nonempty fields: ' + ', '.join(keys))


def _verify(workspace, stage, *, approved=True):
    state = read(workspace / 'stage-state.json')
    pointer = state['latest'].get(stage)
    if not pointer:
        raise WorkflowError(f'Missing {stage} handoff; invoke its own skill first')
    artifact = workspace / pointer['path']
    if sha256(artifact) != pointer['sha256']:
        raise WorkflowError(f'{stage} artifact changed; review invalid')
    document = read(artifact)
    if document.get('registry_sha256') != sha256(REGISTRY) or document.get('validator_sha256') != sha256(__file__):
        raise WorkflowError(f'{stage} handoff rules changed; regenerate this handoff')
    if document.get('rules_sha256') != _rules_digest():
        raise WorkflowError(f'{stage} quality contracts changed; regenerate this handoff')
    if _skill_digest(stage) != document['skill_sha256']:
        raise WorkflowError(f'{stage} skill changed; regenerate this handoff')
    for row in document['files']:
        if not Path(row['path']).is_file() or sha256(row['path']) != row['sha256']:
            raise WorkflowError(f'{stage} attachment changed; return to {stage}')
    for upstream, checksum in document['upstream'].items():
        _, current = _verify(workspace, upstream)
        if current != checksum:
            raise WorkflowError(f'{stage} is stale because {upstream} changed')
    if approved:
        approval = artifact.parent / 'approval.json'
        if not approval.is_file() or read(approval).get('artifact_sha256') != pointer['sha256']:
            raise WorkflowError(f'{stage} awaits human approval; do not skip to the next skill')
    return document, pointer['sha256']


def _dependencies(workspace, stage):
    item = next(s for s in registry()['stages'] if s['command'] == stage)
    return {name: _verify(workspace, name)[1] for name in item['requires']}


def _protected(spec):
    factual_sources = {f['source_id'] for f in spec['facts']}
    return {'sources': [s for s in spec['sources'] if s['id'] in factual_sources], 'facts': spec['facts'],
            'slides': [{'id': s['id'], 'title': s['title'], 'message': s['message'],
                        'data': [{k: e[k] for k in ('id', 'fact_refs', 'text_template', 'chart', 'table', 'diagram') if k in e}
                                 | ({'text': e['text']} if e.get('fact_refs') and e['type'] == 'text' else {})
                                 for e in s['elements'] if e.get('fact_refs') or e['type'] in ('chart','table','diagram')]} for s in spec['slides']]}


def validate_stage(stage, payload, base, upstream, input_path=None):
    """Return referenced files and unresolved required inputs; never invent work."""
    if not isinstance(payload, dict): raise WorkflowError('Stage input must be a JSON object')
    files, missing = [], []
    quality_mode=(payload.get('quality_profile')=='quality-v1' if stage=='intake' else
                  upstream.get('intake',{}).get('payload',{}).get('quality_profile')=='quality-v1')
    from .production_materials import MODE,validate_brief,verify_pack,composition_sources_match,validate_packed_images
    production_mode=(payload if stage=='intake' else upstream.get('intake',{}).get('payload',{})).get('production_mode')==MODE
    def attachment(key, obj=payload):
        p = _path(obj[key], base)
        files.append(p)
        return p
    if stage == 'intake':
        if payload.get('production_mode') not in (None,MODE):raise WorkflowError('Unsupported production mode')
        if payload.get('quality_profile','legacy') not in ('legacy','quality-v1'):
            raise WorkflowError('Unsupported quality profile')
        for key in ('topic', 'audience', 'goal', 'language', 'delivery_mode', 'brand', 'editability'):
            if not isinstance(payload.get(key), str) or not payload[key].strip(): missing.append(key)
        if payload.get('language') not in ('zh-CN', 'en', 'zh-CN-en'): missing.append('supported language')
        if payload.get('delivery_mode') not in ('presented', 'read_alone'): missing.append('delivery mode')
        if type(payload.get('slide_count')) is not int or not 8 <= payload['slide_count'] <= 20: missing.append('8–20 page count')
        if payload.get('aspect_ratio') != '16:9': missing.append('16:9 aspect ratio')
        questions = payload.get('open_questions', [])
        if not isinstance(questions, list): raise WorkflowError('open_questions must be a list')
        for q in questions:
            if not isinstance(q, dict) or not q.get('question'): raise WorkflowError('Every question needs question text')
            if q.get('required', True) and not q.get('answer'): missing.append(q['question'])
        for material in payload.get('material_files', []): files.append(_path(material, base))
    elif stage == 'outline':
        _text(payload, 'narrative', 'source_review_notes')
        request = upstream['intake']['payload']
        pages = payload['slides']
        if len(pages) != request['slide_count'] or len({p['id'] for p in pages}) != len(pages):
            raise WorkflowError('Outline page count/IDs differ from approved requirements')
        sources = {s['id']: s for s in payload['sources']}
        facts = {f['id']: f for f in payload['facts']}
        if len(sources) != len(payload['sources']) or len(facts) != len(payload['facts']):
            raise WorkflowError('Duplicate source/fact ID')
        for source in sources.values():
            _text(source, 'id', 'locator')
            if source.get('kind') not in ('file','url','inline','demo') or type(source.get('is_demo')) is not bool:
                raise WorkflowError('Source kind/demo classification is invalid')
            if source['kind'] in ('file', 'demo'): files.append(_path(source['locator'], ROOT))
        for fact in facts.values():
            _text(fact, 'id', 'source_id', 'unit', 'scope', 'locator', 'period', 'metric')
            if fact['source_id'] not in sources or 'value' not in fact or type(fact.get('is_demo')) is not bool:
                raise WorkflowError('Fact is missing provenance/value or demo classification')
            if sources[fact['source_id']]['is_demo'] and not fact['is_demo']: raise WorkflowError('Demo presented as real data')
            if sources[fact['source_id']]['kind'] == 'demo':
                value = read(_path(sources[fact['source_id']]['locator'], ROOT))
                for part in fact['locator'].lstrip('/').split('/'): value = value[part]
                if value != fact: raise WorkflowError('Fact differs from its original record')
        for page in pages:
            _text(page, 'id', 'takeaway', 'speaker_intent', 'visual_intent')
            if not isinstance(page.get('evidence_refs'), list): raise WorkflowError('Each page needs explicit evidence_refs')
            if any(ref not in sources and ref not in facts for ref in page['evidence_refs']): raise WorkflowError('Unknown evidence reference')
        if production_mode or 'production_brief' in payload:
            if not payload.get('production_brief'):raise WorkflowError('Detailed production_brief attachment required')
            validate_brief(read(attachment('production_brief')),payload)
        if quality_mode or 'quality_plan' in payload:
            if not payload.get('quality_plan'):raise WorkflowError('quality-v1 outline requires quality_plan attachment')
            from .quality import validate_content_plan
            plan_path=attachment('quality_plan');plan=read(plan_path)
            errors=validate_content_plan(plan,payload,request)
            if errors:raise WorkflowError('; '.join(errors))
            if 'outline_sha256' in plan and input_path is not None and plan['outline_sha256']!=sha256(input_path):
                raise WorkflowError('Quality plan belongs to different outline bytes')
            if 'baseline' in plan:
                baseline=_path(plan['baseline']['path'],plan_path.parent);files.append(baseline)
                if sha256(baseline)!=plan['baseline']['sha256']:raise WorkflowError('Quality baseline changed')
    elif stage == 'template':
        if production_mode:
            if not payload.get('materials_pack'):raise WorkflowError('Prepare task-local materials before final template selection')
            pack,tracked=verify_pack(attachment('materials_pack'),upstream['outline']['payload']);files.extend(tracked)
            outline_doc=upstream['outline'];approved_brief=_path(outline_doc['payload']['production_brief'],outline_doc['base_dir'])
            if sha256(approved_brief)!=pack['brief_sha256']:raise WorkflowError('Materials pack changed the approved detailed brief')
        _text(payload, 'selection_rationale', 'asset_guidance', 'editability_policy')
        design = read(attachment('design_system'))
        template = attachment('template_path')
        with ZipFile(template) as package:
            if 'ppt/presentation.xml' not in package.namelist(): raise WorkflowError('Not a PowerPoint template')
            actual_names = set()
            for name in package.namelist():
                if name.startswith('ppt/slideLayouts/slideLayout') and name.endswith('.xml'):
                    element = ET.fromstring(package.read(name)).find('{http://schemas.openxmlformats.org/presentationml/2006/main}cSld')
                    if element is not None: actual_names.add(element.get('name'))
            if any(l.get('name', l['key']) not in actual_names for l in design['layouts']):
                raise WorkflowError('Declared layouts are absent from the actual template')
        if set(payload['layout_keys']) != {x['key'] for x in design['layouts']}: raise WorkflowError('Template layout registry differs from design system')
        if not payload.get('preview_paths'): raise WorkflowError('Template needs actual preview images')
        for item in payload['preview_paths']:
            p = _path(item, base); files.append(p)
            with Image.open(p) as image: image.verify()
        if not design.get('font') or not design.get('colors'): raise WorkflowError('Template must define fonts and colors')
        if quality_mode:
            from .quality import validate_layouts
            previous=upstream['outline'];plan=read(_path(previous['payload']['quality_plan'],previous['base_dir']))
            errors=validate_layouts(design,plan)
            if errors:raise WorkflowError('; '.join(errors))
    elif stage == 'compose':
        _text(payload, 'implementation_notes')
        spec = read(attachment('deck_spec')); deck = attachment('deck')
        errors = validate(spec, 'deck')
        if errors: raise WorkflowError('; '.join(errors))
        outline = upstream['outline']['payload']
        if not composition_sources_match(spec,outline): raise WorkflowError('Composition changed approved sources or facts, or added unregistered origins')
        if production_mode:
            template_doc=upstream['template'];pack_path=_path(template_doc['payload']['materials_pack'],template_doc['base_dir'])
            pack,tracked=verify_pack(pack_path,outline);files.extend(tracked)
            validate_packed_images(spec,pack)
        if [(s['id'], s['title']) for s in spec['slides']] != [(s['id'], s['takeaway']) for s in outline['slides']]:
            raise WorkflowError('Composition changed the approved outline; return to outline skill')
        if any(page['message'] != want['takeaway'] for page,want in zip(spec['slides'],outline['slides'])):
            raise WorkflowError('Composition changed the approved main message; return to outline skill')
        design_doc = upstream['template']
        design = read(_path(design_doc['payload']['design_system'], design_doc['base_dir']))
        if any(s['layout'] not in {l['key'] for l in design['layouts']} for s in spec['slides']): raise WorkflowError('Composition uses an unapproved layout')
        _native_template(spec, deck, design)
        if quality_mode:
            from .quality import validate_layouts
            plan=read(_path(upstream['outline']['payload']['quality_plan'],upstream['outline']['base_dir']))
            errors=validate_layouts(design,plan,spec)
            if errors:raise WorkflowError('; '.join(errors))
        ledger, native = check_ledger(spec, ROOT), inspect_native(deck, spec)
        if ledger.status == 'failed' or native.status != 'passed': raise WorkflowError('Content or editable native objects do not match composition spec')
        files.extend(_path(a['path'], ROOT) for a in spec.get('assets', []))
    elif stage == 'polish':
        _text(payload, 'visual_notes', 'copy_notes')
        composed = upstream['compose']
        before = read(_path(composed['payload']['deck_spec'], composed['base_dir']))
        after = read(attachment('deck_spec')); deck = attachment('deck')
        errors = validate(after, 'deck')
        if errors: raise WorkflowError('; '.join(errors))
        if _protected(before) != _protected(after): raise WorkflowError('Polish changed facts, approved headlines or structural content; return to outline/compose')
        native = inspect_native(deck, after)
        if native.status != 'passed' or check_ledger(after, ROOT).status == 'failed': raise WorkflowError('Polished deck differs from its spec or factual ledger')
        if not isinstance(payload.get('changes'), list): raise WorkflowError('Explicit changes list required, including empty for no change')
        for change in payload['changes']: _text(change, 'element_id', 'change', 'reason')
        design_doc = upstream['template']
        design = read(_path(design_doc['payload']['design_system'], design_doc['base_dir']))
        _native_template(after, deck, design)
        palette = set(design['colors'].values()) | {'FFFFFF'}
        layout_backgrounds={l['key']:l.get('background_color',design['colors']['background']) for l in design['layouts']}
        for page in after['slides']:
            if page.get('background_color') != layout_backgrounds.get(page['layout']): raise WorkflowError('Brand/background changed; return to template')
            for e in page['elements']:
                style = e.get('style', {})
                if style.get('font_face', design['font']) != design['font'] or style.get('color', design['colors']['ink']) not in palette:
                    raise WorkflowError('Brand font/color changed; return to template')
        files.extend(_path(a['path'], ROOT) for a in after.get('assets', []))
    elif stage == 'review':
        _text(payload, 'assessment')
        polished = upstream['polish']
        target = _path(polished['payload']['deck'], polished['base_dir'])
        qa_path, render_path, visual_path = [attachment(k) for k in ('qa_report', 'render_manifest', 'visual_review')]
        qa, render, visual = read(qa_path), read(render_path), read(visual_path)
        if validate(qa, 'qa'): raise WorkflowError('Invalid QA report')
        checksum = sha256(target)
        if qa['artifact']['sha256'] != checksum or render.get('input_sha256') != checksum: raise WorkflowError('Review targets a different deck')
        if render.get('status') != 'passed': raise WorkflowError('Verified rendered pages required')
        spec = read(_path(polished['payload']['deck_spec'], polished['base_dir']))
        count = len(spec['slides'])
        if render.get('expected_slide_count') != count or [i['slide'] for i in render['images']] != list(range(1,count+1)): raise WorkflowError('Missing or unordered rendered pages')
        images = []
        for row in render['images']:
            p = _path(row['path'], base); files.append(p)
            if sha256(p) != row['sha256']: raise WorkflowError('Rendered page changed after review')
            with Image.open(p) as image:
                if list(image.size) != row['size_px']: raise WorkflowError('Render dimensions changed')
            images.append({'slide': row['slide'], 'sha256': row['sha256']})
        binding = visual.get('binding', {})
        if binding.get('deck_sha256') != checksum or binding.get('images') != images: raise WorkflowError('Visual record belongs to other images/deck')
        if binding.get('spec_sha256') != sha256(_path(polished['payload']['deck_spec'], polished['base_dir'])): raise WorkflowError('Visual record belongs to another spec')
        if visual.get('method') not in ('host-image-inspection', 'visual-api') or not visual.get('reviewer'):
            raise WorkflowError('Visual audit needs its actual method and reviewer')
        pages = visual.get('pages', [])
        allowed = {'passed','failed','needs_review','unverified'}
        if visual.get('status') not in allowed or sorted(p.get('slide') for p in pages) != list(range(1,count+1)):
            raise WorkflowError('Visual audit must cover each page once and report an explicit status')
        if any(p.get('status') not in allowed or not p.get('notes') for p in pages) or not visual.get('consistency_notes') or not visual.get('content_notes'):
            raise WorkflowError('Visual audit requires concrete page, consistency and content observations')
        automated_path = attachment('automated_qa')
        automated = read(automated_path)
        if binding.get('qa_sha256') != sha256(automated_path): raise WorkflowError('Visual review did not inspect this automated QA report')
        if automated['artifact']['sha256'] != checksum or automated['issues'] != qa['issues']:
            raise WorkflowError('QA findings changed after visual review')
        expected_unknown = set(automated['coverage']['unknown']) - ({'visual-review-not-executed'} if visual['status']=='passed' else set())
        if set(qa['coverage']['unknown']) != expected_unknown or any(automated['stages'][k] != qa['stages'][k] for k in automated['stages'] if k != 'visual'):
            raise WorkflowError('Review cannot silently resolve automated unknown checks')
        visual_failed = visual['status']=='failed' or any(p['status']=='failed' for p in pages)
        visual_unknown = visual['status']=='unverified' or any(p['status']=='unverified' for p in pages)
        visual_pending = visual['status']=='needs_review' or any(p['status']=='needs_review' for p in pages)
        decision = 'failed' if qa['status'] == 'failed' or visual_failed else 'unverified' if qa['coverage']['unknown'] or qa['status'] != 'passed' or visual_unknown else 'needs_review' if visual_pending or any(i['severity']=='warning' for i in qa['issues']) else 'passed'
        if quality_mode:
            from .quality import validate_quality_review,review_decision,combine_decisions
            previous=upstream['outline'];plan=read(_path(previous['payload']['quality_plan'],previous['base_dir']))
            if not payload.get('quality_review'):raise WorkflowError('quality-v1 review requires quality_review attachment')
            quality=read(attachment('quality_review'))
            errors=validate_quality_review(quality,plan,spec)
            if errors:raise WorkflowError('; '.join(errors))
            if any(quality['binding'].get(k)!=binding.get(k) for k in quality['binding']):raise WorkflowError('Quality review belongs to different source/export evidence')
            decision=combine_decisions(decision,review_decision(quality))
        if payload.get('decision') != decision: raise WorkflowError('Review decision cannot hide QA failures, unknown checks or warnings')
    return list(dict.fromkeys(files)), missing


def _native_template(spec, deck, design):
    lookup = {l['key']: l.get('name', l['key']) for l in design['layouts']}
    presentation = Presentation(deck)
    if len(presentation.slides) != len(spec['slides']): raise WorkflowError('Native slide count differs from spec')
    for page, slide in zip(spec['slides'],presentation.slides):
        if slide.slide_layout.name != lookup.get(page['layout']):
            raise WorkflowError('Actual native template layout differs from the approved design')


def stage_action(stage, workspace, *, input_path=None, approve=None, reviewer=None, evidence=None):
    workspace = fresh_run(workspace)
    route = skill_route(stage)
    item = next(s for s in registry()['stages'] if s['command'] == stage)
    if input_path is None and approve is None:
        status = 'needs_skill_execution'
        existing = None
        if (workspace / 'stage-state.json').is_file():
            try:
                _dependencies(workspace, stage)
                if stage in read(workspace / 'stage-state.json')['latest']:
                    doc, checksum = _verify(workspace, stage, approved=False)
                    existing = {'artifact_sha256': checksum, 'status': doc['status']}
            except WorkflowError as exc:
                status = 'blocked'
                existing = {'reason': str(exc)}
        elif item['requires']:
            status = 'blocked'; existing = {'reason': 'Approved upstream handoff required'}
        return {'status': status, 'route': route, 'requires': item['requires'], 'expected_output': item['output'],
                'current': existing, 'instruction': 'Host reads this SKILL.md, performs its task, and submits a concrete artifact with --input; no skill work was executed by this CLI.'}
    if input_path is not None and approve is not None: raise WorkflowError('Submit and approve are separate actions')
    if not workspace.exists():
        if stage != 'intake': raise WorkflowError('Start with intake')
        workspace.mkdir(parents=True)
        write(workspace / 'stage-state.json', {'version': 1, 'latest': {}, 'history': []})
    with locked(workspace):
        dependencies = _dependencies(workspace, stage)
        state = read(workspace / 'stage-state.json')
        if approve is not None:
            doc, checksum = _verify(workspace, stage, approved=False)
            if checksum != approve or doc['status'] == 'needs_input' or not reviewer or not evidence:
                raise WorkflowError('Approval needs this exact artifact hash, resolved required inputs, reviewer and human evidence')
            approval = workspace / state['latest'][stage]['path']
            write(approval.parent / 'approval.json', {'artifact_sha256': checksum, 'reviewer': reviewer, 'evidence': evidence,
                  'meaning': 'stage handoff approval only; not release approval', 'upstream': dependencies})
            return {'status': 'approved', 'stage': stage, 'route': route, 'artifact_sha256': checksum,
                    'release_allowed': stage == 'review' and doc['payload']['decision'] == 'passed'}
        path = _path(input_path, Path.cwd())
        payload = read(path)
        upstream = {}
        for previous in registry()['stages']:
            if previous['command'] == stage: break
            upstream[previous['command']] = _verify(workspace, previous['command'])[0]
        files, missing = validate_stage(stage, payload, path.parent, upstream, input_path=path)
        version = 1+sum(h['stage'] == stage for h in state['history'])
        directory = workspace / f'{stage}-{version:03d}'
        directory.mkdir()
        artifact = directory / item['output']
        write(artifact, {'stage': stage, 'payload': payload, 'base_dir': str(path.parent), 'upstream': dependencies,
              'skill_sha256': _skill_digest(stage), 'registry_sha256':sha256(REGISTRY), 'validator_sha256':sha256(__file__), 'rules_sha256':_rules_digest(),
              'files': [{'path': str(p), 'sha256': sha256(p)} for p in files],
              'status': 'needs_input' if missing else 'needs_review', 'missing': missing})
        checksum = sha256(artifact)
        state['latest'][stage] = {'path': str(artifact.relative_to(workspace)), 'sha256': checksum}
        state['history'].append({'stage': stage, 'version': version, 'sha256': checksum})
        write(workspace / 'stage-state.json', state)
        return {'status': 'needs_input' if missing else 'needs_review', 'stage': stage, 'route': route,
                'artifact': str(artifact), 'artifact_sha256': checksum, 'missing': missing,
                'next_skill': next((s['skill'] for i,s in enumerate(registry()['stages']) if i and registry()['stages'][i-1]['command']==stage), None)}
