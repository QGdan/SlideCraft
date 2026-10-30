"""Declared compiler boundaries; no silent fallback from unsupported charts."""
import json,math,re
from datetime import date
from pathlib import Path
CAPABILITIES=Path(__file__).resolve().parents[1]/'engine/capabilities.json'
def capabilities():return json.loads(CAPABILITIES.read_text(encoding='utf-8'))
def validate_chart(chart,version='0.1'):
    errors=[];caps=capabilities();kind=chart['kind'];values=[v for s in chart['series'] for v in s['values']]
    if version=='0.1':
        if 'options' in chart or 'semantics' in chart:errors.append('Extended chart options require schema_version 0.2')
        return errors
    if kind not in caps['chart_kinds']:errors.append(f'Unsupported native chart kind: {kind}')
    if len(chart['categories'])>caps['max_categories'] or len(chart['series'])>caps['max_series']:errors.append('Chart exceeds declared category/series capacity')
    if len(set(chart['categories']))!=len(chart['categories']):errors.append('Chart categories must be unique')
    if len({s['name'] for s in chart['series']})!=len(chart['series']):errors.append('Chart series names must be unique')
    semantics=chart.get('semantics',{})
    if not semantics.get('reason'):errors.append('Extended chart requires semantic selection reason')
    if kind=='line':
        if semantics.get('task')!='trend' or semantics.get('category_order')!='chronological':errors.append('Line chart requires declared chronological trend data')
    elif semantics.get('task')!='comparison':errors.append('Bar/column charts require comparison semantics')
    if chart['unit']=='%' and any(v<0 or v>100 for v in values):errors.append('Percentage values must use the 0–100 convention')
    options=chart.get('options',{})
    preset=options.get('presentation_preset')
    if preset:
        definitions={'focus-comparison':('bar',6,1),'series-comparison':('column',4,2),'focus-trend':('line',8,2)}
        if preset not in definitions:errors.append('Unknown chart presentation preset')
        else:
            expected,category_limit,series_limit=definitions[preset]
            if kind!=expected or not 2<=len(chart['categories'])<=category_limit or len(chart['series'])>series_limit:errors.append('Chart presentation preset capacity/type mismatch')
            if preset=='focus-comparison' and len(options.get('emphasize_categories',[]))!=1:errors.append('Focused comparison requires exactly one emphasized category')
            if preset=='series-comparison' and len(chart['series'])!=2:errors.append('Series comparison requires two series')
            if preset=='focus-trend':
                categories=chart['categories']
                try:
                    for c in categories:
                        if not re.fullmatch(r'\d{4}-\d{2}',c):raise ValueError()
                        date.fromisoformat(c+'-01')
                    if categories!=sorted(set(categories)):raise ValueError()
                except ValueError:errors.append('Trend presentation requires valid distinct ascending ISO months')
    if set(options.get('emphasize_categories',[]))-set(chart['categories']):errors.append('Unknown emphasis category')
    if set(options.get('emphasize_series',[]))-{s['name'] for s in chart['series']}:errors.append('Unknown emphasis series')
    if options.get('emphasize_categories') and (len(chart['series'])!=1 or kind=='line'):errors.append('Category emphasis supports a single bar/column series only')
    if options.get('emphasize_series') and options.get('emphasize_categories'):errors.append('Select either category or series emphasis')
    lo=options.get('axis_min',min(0,min(values)));hi=options.get('axis_max',max(1,max(values)))
    if lo>=hi or lo>min(0,min(values)) or hi<max(values):errors.append('Axis must cover all data and zero without clipping')
    return errors
