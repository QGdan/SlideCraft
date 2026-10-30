"""Editable information exhibits, returned as ordinary native spec elements.

Original components, not decorative card templates. Typography fit still needs
target-render review; unsupported density fails instead of shrinking silently.
"""
import math,re
def compose_exhibit(kind,element_id,items,rect,theme):
    if kind not in ('process','comparison','action'):raise ValueError('Unsupported exhibit kind')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}',element_id):raise ValueError('Stable element ID up to 40 characters required')
    if not isinstance(items,list) or not 2<=len(items)<=6 or (kind=='comparison' and len(items)!=2):raise ValueError('Exhibit item capacity exceeded')
    if set(rect)!={'x','y','w','h'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in rect.values()):raise ValueError('Finite rectangle required')
    if rect['x']<0 or rect['y']<0 or rect['w']<len(items)*1.45 or rect['h']<2:raise ValueError('Exhibit region too small')
    for item in items:
        if not isinstance(item,dict) or set(item)-{'title','body','output'} or not isinstance(item.get('title'),str) or not item['title'] or not isinstance(item.get('body'),str) or not isinstance(item.get('output',''),str):raise ValueError('Title/body content required')
        if len(item['title'])>18 or len(item['body'])>36 or len(item.get('output',''))>24:raise ValueError('Content capacity exceeded; rewrite or split the exhibit')
        if kind=='action' and not item.get('output'):raise ValueError('Action item requires verifiable output')
    colors=theme['colors'];font=theme['font'];out=[];gap=.35;step=rect['w']/len(items)
    def text(suffix,text,x,y,w,h,bold=False,color=None):
        out.append({'id':f'{element_id}-{suffix}','type':'text','role':'body','rect':dict(x=x,y=y,w=w,h=h),'editability_requirement':'native','fact_refs':[],
            'text':text,'style':{'font_face':font,'font_size_pt':18,'color':color or colors['ink'],'bold':bold}})
    def line(suffix,x,y,w,h,arrow=False):
        out.append({'id':f'{element_id}-{suffix}','type':'line','role':'diagram','rect':dict(x=x,y=y,w=w,h=h),'editability_requirement':'native',
            'fact_refs':[],'arrow_end':arrow,'style':{'color':colors['accent']}})
    for i,item in enumerate(items):
        x=rect['x']+i*step;w=step-gap
        text(f'n{i+1}-title',item['title'],x,rect['y'],w,.65,True,colors['accent'])
        text(f'n{i+1}-body',item['body'],x,rect['y']+.78,w,rect['h']-1.45 if kind=='action' else rect['h']-.78)
        if kind=='action':text(f'n{i+1}-output',item['output'],x,rect['y']+rect['h']-.55,w,.55,False,colors.get('muted',colors['ink']))
        if i<len(items)-1:
            if kind=='comparison':line(f'divider{i+1}',x+step-gap/2,rect['y'],.01,rect['h'])
            else:line(f'edge{i+1}',x+w+.03,rect['y']+.28,gap-.09,.01,True)
    return out

def compose_vertical_action(element_id,items,rect,theme):
    """Native three-column step rows for a text/image split page, not card art."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}',element_id):raise ValueError('Stable element ID required')
    if not isinstance(items,list) or not 2<=len(items)<=4:raise ValueError('Vertical action supports 2–4 steps')
    if set(rect)!={'x','y','w','h'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in rect.values()):raise ValueError('Finite rectangle required')
    if rect['x']<0 or rect['y']<0 or rect['w']<6.2 or rect['h']/len(items)<.8:raise ValueError('Vertical action region too small')
    for item in items:
        if not isinstance(item,dict) or set(item)!={'title','body','output'} or not all(isinstance(v,str) and v.strip() for v in item.values()):raise ValueError('Title/body/output required')
        if len(item['title'])>6 or len(item['body'])>16 or len(item['output'])>9:raise ValueError('Vertical action capacity exceeded; use a wider layout')
    out=[];c=theme['colors'];step=rect['h']/len(items)
    for i,item in enumerate(items):
        y=rect['y']+i*step
        for key,dx,w,color,bold in [('title',.3,1.3,c['accent'],True),('body',1.85,2.2,c['ink'],False),('output',4.35,rect['w']-4.35,c['muted'],False)]:
            out.append(dict(id=f'{element_id}-n{i+1}-{key}',type='text',role='body',rect=dict(x=rect['x']+dx,y=y,w=w,h=.72),editability_requirement='native',fact_refs=[],text=item[key],style=dict(font_face=theme['font'],font_size_pt=18,color=color,bold=bold)))
        if i<len(items)-1:
            out.append(dict(id=f'{element_id}-edge{i+1}',type='line',role='diagram',rect=dict(x=rect['x'],y=y+.36,w=.01,h=step),editability_requirement='native',fact_refs=[],arrow_end=True,style={'color':c['accent']}))
    return out
