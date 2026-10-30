"""Task-specific content and review contracts inspired by open-source workflows.

Original implementation; upstream methods and boundaries in docs/开源融合记录.md.
"""
from decimal import Decimal
import math
from .contracts import validate

def validate_content_plan(plan,outline,requirements=None):
    errors=validate(plan,'content-plan')
    if errors:return errors
    pages=plan['slides'];expected=outline['slides'];refs={s['id'] for s in outline['sources']}|{f['id'] for f in outline['facts']}
    facts={f['id']:f for f in outline['facts']}
    if [p['id'] for p in pages]!=[p['id'] for p in expected]:errors.append('Content plan page IDs/order differ from outline')
    if len({p['id'] for p in pages})!=len(pages):errors.append('Duplicate content plan page IDs')
    if 'duration_seconds' in plan and sum(p.get('duration_seconds',0) for p in expected)!=plan['duration_seconds']:errors.append('Content plan talk timing differs')
    if requirements and requirements.get('duration_minutes') is not None and plan.get('duration_seconds')!=round(requirements['duration_minutes']*60):errors.append('Content plan duration differs from requirements')
    if set(plan.get('pilot_slides',[]))-{p['id'] for p in pages}:errors.append('Unknown pilot slide')
    for p,w in zip(pages,expected):
        prefix=p['id']+': '
        if len(set(p['quality_checks']))!=len(p['quality_checks']):errors.append(prefix+'duplicate task-specific questions')
        if p['claim']!=w['takeaway'] or p['evidence_refs']!=w['evidence_refs']:errors.append(prefix+'claim/evidence differ from outline')
        if set(p['evidence_refs'])-refs:errors.append(prefix+'unknown evidence reference')
        case=p['case']
        if case['kind']=='teaching_example' and not any(x in case['label'].lower() for x in ('示例','example')):errors.append(prefix+'teaching example needs visible label')
        if case['kind']=='source_paraphrase' and (not case['source_refs'] or set(case['source_refs'])-set(p['evidence_refs'])):errors.append(prefix+'case source not cited')
        if p['claim_kind']=='fact' and not p['evidence_refs']:errors.append(prefix+'factual claim has no evidence')
        chart=p['chart']
        if chart:
            ids=chart['data_refs']
            if set(ids)-set(facts) or set(ids)-set(p['evidence_refs']):errors.append(prefix+'chart references unknown/uncited facts')
            if set(chart['emphasis_refs'])-set(ids):errors.append(prefix+'chart emphasis not in data')
            if any(facts[i]['unit']!=chart['unit'] for i in ids if i in facts):errors.append(prefix+'chart units differ')
            if chart['task']=='composition' and not(chart.get('mutually_exclusive') is True and chart.get('exhaustive') is True):errors.append(prefix+'composition needs verified exclusive complete categories')
        for d in p['derived']:
            if set(d['inputs'])-set(facts):errors.append(prefix+'unknown derivation input');continue
            a,b=[facts[i] for i in d['inputs']]
            if a['source_id']!=b['source_id'] or a.get('period')!=b.get('period') or a['unit']!=b['unit']:errors.append(prefix+'incomparable derivation inputs');continue
            if not all(isinstance(x['value'],(int,float)) and not isinstance(x['value'],bool) and math.isfinite(x['value']) for x in (a,b)):
                errors.append(prefix+'derivation requires numeric inputs');continue
            av,bv=Decimal(str(a['value'])),Decimal(str(b['value']))
            if d['operation']=='divide' and bv==0:errors.append(prefix+'zero denominator');continue
            expected_value=av-bv if d['operation']=='subtract' else av/bv
            unit=('百分点' if a['unit']=='%' else a['unit']) if d['operation']=='subtract' else '倍'
            if abs(expected_value-Decimal(str(d['value'])))>Decimal('0.000000001') or d['unit']!=unit:errors.append(prefix+'derived value/unit mismatch')
    return errors

def validate_quality_review(report,plan,spec=None):
    errors=validate(report,'quality-review')
    if errors:return errors
    wanted={(p['id'],q) for p in plan['slides'] for q in p['quality_checks']}
    actual=[(c['slide_id'],c['question']) for c in report['checks']]
    if len(actual)!=len(set(actual)) or set(actual)!=wanted:errors.append('Quality review must answer every task-specific question exactly once')
    if len({c['id'] for c in report['checks']})!=len(report['checks']):errors.append('Duplicate review check ID')
    ids={p['id'] for p in plan['slides']}
    if len({f['id'] for f in report['findings']})!=len(report['findings']):errors.append('Duplicate finding ID')
    elements={p['id']:{e['id'] for e in p['elements']} for p in spec['slides']} if spec else None
    for c in report['checks']:
        if c['answer']!='unverified' and not c['evidence']:errors.append('Answered review check lacks evidence')
    for f in report['findings']:
        if f['slide_id'] is not None and f['slide_id'] not in ids:errors.append('Finding refers to unknown slide')
        if f['status']=='resolved' and not f['resolution_evidence']:errors.append('Resolved finding lacks recheck evidence')
        if elements is not None and f['element_id'] is not None and f['element_id'] not in elements.get(f['slide_id'],set()):errors.append('Finding element not on declared slide')
    return errors

def review_decision(report):
    states=[x['status'] for x in report['dimensions'].values()]
    if 'failed' in states or any(c['answer']=='no' for c in report['checks']) or any(f['status']=='open' and f['severity']=='error' for f in report['findings']):return 'failed'
    if 'unverified' in states or any(c['answer']=='unverified' for c in report['checks']):return 'unverified'
    if 'needs_review' in states or any(f['status']=='open' for f in report['findings']):return 'needs_review'
    return 'passed'

def review_scaffold(plan):
    """An unanswered review contract, never a generated acceptance judgment."""
    return {'schema_version':'quality-review/1','binding':{'deck_sha256':'0'*64,'spec_sha256':'0'*64,'qa_sha256':'0'*64,'images':[]},
        'dimensions':{k:{'status':'unverified','notes':'尚未执行本维度审核'} for k in ('content','design','engineering')},'findings':[],
        'checks':[{'id':f"{p['id']}-q{i+1}",'slide_id':p['id'],'question':q,'answer':'unverified','evidence':[]} for p in plan['slides'] for i,q in enumerate(p['quality_checks'])]}

def validate_layouts(design,plan,spec=None):
    """Template slots/capacities are declared, not inferred from a pretty background."""
    errors=[];variants=design.get('semantic_layouts',{})
    allowed={x['key'] for x in design['layouts']}
    if not isinstance(variants,dict) or not variants:return ['Quality template requires semantic_layouts']
    for key,variant in variants.items():
        if key not in allowed or not isinstance(variant,dict):errors.append('Unknown/invalid semantic layout');continue
        carriers=variant.get('carriers')
        if not isinstance(carriers,list) or not carriers or not all(isinstance(c,str) and c for c in carriers):errors.append('Layout requires supported carriers')
        for field in ('max_body_characters','max_chart_categories','max_chart_series','min_body_font_pt'):
            if not isinstance(variant.get(field),(int,float)) or isinstance(variant.get(field),bool) or not math.isfinite(variant[field]) or variant[field]<=0:errors.append('Layout needs positive capacity: '+field)
    if errors:return errors
    supported={c for v in variants.values() for c in v['carriers']}
    for p in plan['slides']:
        if p['exhibit']['carrier'] not in supported:errors.append(p['id']+': no approved layout supports the planned carrier')
    if spec:
        plans={p['id']:p for p in plan['slides']}
        for page in spec['slides']:
            v=variants.get(page['layout']);p=plans.get(page['id'])
            if not v or not p or p['exhibit']['carrier'] not in v['carriers']:errors.append(page['id']+': layout carrier mismatch');continue
            body=[e for e in page['elements'] if e['type']=='text' and e['role'] in ('body','data')]
            if sum(len(e['text']) for e in body)>v['max_body_characters']:errors.append(page['id']+': layout text capacity exceeded')
            if any(e.get('style',{}).get('font_size_pt',v['min_body_font_pt'])<v['min_body_font_pt'] for e in body):errors.append(page['id']+': body font below approved minimum')
            for e in page['elements']:
                if e['type']=='chart' and (len(e['chart']['categories'])>v['max_chart_categories'] or len(e['chart']['series'])>v['max_chart_series']):errors.append(page['id']+': layout chart capacity exceeded')
                if e['type']=='chart' and spec.get('schema_version')=='0.2':
                    options=e['chart'].get('options',{});colors=options.get('colors',{})
                    if not all(k in colors for k in ('accent','muted','ink')) or options.get('font_face')!=design.get('font'):errors.append(page['id']+': chart needs explicit approved palette/font')
                    palette={c.upper() for c in design.get('colors',{}).values()}
                    if any(c.upper() not in palette for c in [colors.get('accent',''),colors.get('muted',''),colors.get('ink',''),*colors.get('series',[])]):errors.append(page['id']+': chart palette differs from template')
                    if len(e['chart']['series'])>1 and not options.get('emphasize_series') and len(colors.get('series',[]))<len(e['chart']['series']):errors.append(page['id']+': multi-series chart needs approved series colors')
    return errors

def combine_decisions(*states):
    order={'passed':0,'needs_review':1,'unverified':2,'failed':3}
    return max(states,key=lambda x:order[x])
