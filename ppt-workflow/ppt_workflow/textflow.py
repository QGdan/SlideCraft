"""Measured Chinese/Latin line breaks. Source spans survive wrapping and pagination."""
from functools import lru_cache
from pathlib import Path
import math
import re
from PIL import ImageFont

NO_START=set('，。；：！？、）》】”’%％,.!?;:)]}')
NO_END=set('（《【“‘([{')
TOKEN=re.compile(r'[A-Za-z0-9]+(?:[-./_:][A-Za-z0-9]+)*|[^A-Za-z0-9]')

@lru_cache(maxsize=32)
def measured_font(size,bold=False):
    path=Path('C:/Windows/Fonts')/('msyhbd.ttc' if bold else 'msyh.ttc')
    if not path.is_file():raise ValueError('Microsoft YaHei metrics unavailable')
    return ImageFont.truetype(str(path),round(size*2))

def measure_lines(text,width,size,bold=False):
    """Return contiguous source spans; only inserted wraps change visible copy.

    Uses conservative YaHei advance widths, not a claim about Office line layout.
    An unbreakable Latin token wider than its region requests another layout.
    """
    if not isinstance(text,str) or not text:raise ValueError('Nonempty text required')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in (width,size)) or width<=.04:raise ValueError('Positive finite text width and size required')
    font=measured_font(size,bold);available=(width-.04)*144;lines=[];offset=0
    for paragraph in text.splitlines(keepends=True):
        visible=paragraph.rstrip('\r\n');tokens=list(TOKEN.finditer(visible));i=0
        if not tokens:lines.append(dict(start=offset,end=offset+len(paragraph),text=''))
        while i<len(tokens):
            j=i
            while j<len(tokens) and font.getlength(visible[tokens[i].start():tokens[j].end()])<=available:j+=1
            if j==i:raise ValueError('Unbreakable token needs a wider layout; rewrite or split explicitly')
            # Pull the preceding character onto the next line when punctuation
            # would otherwise start a line; opening brackets travel forward.
            if j<len(tokens):
                while j>i and (tokens[j].group() in NO_START or tokens[j-1].group() in NO_END):j-=1
                if j==i:raise ValueError('Punctuation cluster needs a wider layout')
            start=tokens[i].start();end=tokens[j-1].end();last=j==len(tokens)
            lines.append(dict(start=offset+start,end=offset+(len(paragraph) if last else end),text=visible[start:end]))
            i=j
        offset+=len(paragraph)
    assert ''.join(text[x['start']:x['end']] for x in lines)==text
    return lines

def line_height(size):return size/72*1.28

def wrap_native(text,width,size,bold=False,max_lines=3):
    lines=measure_lines(text,width,size,bold)
    if len(lines)>max_lines:raise ValueError('Text exceeds recipe capacity; choose another layout or split')
    return '\n'.join(x['text'] for x in lines),len(lines)*line_height(size)+.06
