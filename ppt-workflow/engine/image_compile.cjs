// Original placement adapter. Raster bytes remain unchanged and replaceable.
function compileImage(element,asset){
 const r=element.rect,fit=element.image_fit;
 const base={...r,path:element.asset_path,objectName:element.id};
 if(!fit)return base; // Preserve existing scene behavior.
 if(!['contain','cover'].includes(fit))throw Error('Unsupported image fit');
 if(!asset||![asset.width_px,asset.height_px].every(v=>Number.isFinite(v)&&v>0))throw Error('Registered image dimensions required');
 const f=element.image_focus||{x:.5,y:.5};
 if(![f.x,f.y].every(v=>Number.isFinite(v)&&v>=0&&v<=1))throw Error('Image focus must be between 0 and 1');
 const scale=(fit==='contain'?Math.min:Math.max)(r.w/asset.width_px,r.h/asset.height_px);
 const w=asset.width_px*scale,h=asset.height_px*scale;
 if(fit==='contain')return {...base,x:r.x+(r.w-w)*.5,y:r.y+(r.h-h)*.5,w,h};
 return {...base,w,h,sizing:{type:'crop',w:r.w,h:r.h,x:(w-r.w)*f.x,y:(h-r.h)*f.y}};
}
module.exports={compileImage};
