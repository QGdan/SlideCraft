from pathlib import Path
import json,sys
from PIL import Image,ImageDraw
p=Path(sys.argv[1]).resolve();o=p/'previews';o.mkdir(exist_ok=False)
for r in json.loads((p/'results.json').read_text(encoding='utf-8')):
    if r['status']!='mechanically-passed':continue
    mp=p/r['case']/('render-manifest.json' if r['case']=='existing-ppt-edit' else 'rev-000/qa-000/render-manifest.json')
    manifest=json.loads(mp.read_text(encoding='utf-8'))
    canvas=Image.new('RGB',(1000,310*((len(manifest['images'])+1)//2)),'white');draw=ImageDraw.Draw(canvas)
    for i,image in enumerate(manifest['images']):
        im=Image.open(image['path']).convert('RGB');im.thumbnail((490,276))
        x=(i%2)*500;y=(i//2)*310;canvas.paste(im,(x,y+25));draw.text((x+8,y+6),r['case']+' / '+str(i+1),fill='black')
    canvas.save(o/(r['case']+'.png'))
