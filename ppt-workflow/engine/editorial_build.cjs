const fs=require('fs');
const PptxGenJS=require('pptxgenjs');
const {compileChart}=require('./chart_compile.cjs');
const {compileImage}=require('./image_compile.cjs');
async function main(){
 const [specFile,output,designFile]=process.argv.slice(2); if(!output||fs.existsSync(output))throw Error('Fresh output required');
 const spec=JSON.parse(fs.readFileSync(specFile,'utf8'));const p=new PptxGenJS();
 const shapeKinds=new Set(['rect','roundRect','ellipse','diamond','chevron','hexagon','parallelogram']);
 for(const page of spec.slides)for(const e of page.elements){
  if(e.type==='diagram'||e.type==='smartart')throw Error(`Editorial compiler does not emit ${e.type}; use relationship-prepare for native shapes/connectors, or the supported Office SmartArt route.`);
  if(e.type==='shape'&&!shapeKinds.has(e.shape_kind||'rect'))throw Error(`Unsupported native shape: ${e.shape_kind}`);
 }
 const design=designFile?JSON.parse(fs.readFileSync(designFile,'utf8')):null;
 let layoutNames=null;
 if(design){
  if(spec.blueprint_ref)throw Error('Explicit design cannot override a blueprint');
  if(!design.font||!Array.isArray(design.layouts)||!design.layouts.length)throw Error('Approved design font/layouts required');
  layoutNames=Object.fromEntries(design.layouts.map(l=>[l.key,l.name||l.key]));
  if(Object.keys(layoutNames).length!==design.layouts.length||new Set(Object.values(layoutNames)).size!==design.layouts.length)throw Error('Unique layout keys and native names required');
  if(spec.slides.some(s=>!layoutNames[s.layout]))throw Error('Slide layout absent from design system');
 }
 p.defineLayout({name:'EDITORIAL',width:spec.canvas.width,height:spec.canvas.height});p.layout='EDITORIAL';
 p.title=spec.slides[0]?.title||spec.job_id;p.author='PPT workflow';p.subject=spec.job_id;p.lang='zh-CN';
 p.theme={headFontFace:design?.font||'Microsoft YaHei',bodyFontFace:design?.font||'Microsoft YaHei',lang:'zh-CN'};
 if(layoutNames)for(const name of Object.values(layoutNames))p.defineSlideMaster({title:name,objects:[]});
 if(spec.blueprint_ref)for(const key of [...new Set(spec.slides.map(s=>s.layout))])p.defineSlideMaster({title:key,objects:[]});
 for(const page of spec.slides){
  const s=p.addSlide(layoutNames?{masterName:layoutNames[page.layout]}:spec.blueprint_ref?{masterName:page.layout}:undefined);s.background={color:page.background_color};
  for(const e of page.elements){
   const z=e.style||{},r=e.rect;const o={...r,objectName:e.id,fontFace:z.font_face||'Microsoft YaHei',fontSize:z.font_size_pt||22,color:z.color||'162E3B',bold:!!z.bold,align:z.align||'left',margin:0,wrap:true,valign:'mid',paraSpaceAfterPt:0};
   if(e.type==='text')s.addText(e.text,o);
   else if(e.type==='image')s.addImage(compileImage(e,(spec.assets||[]).find(a=>a.id===e.asset_id)));
   else if(e.type==='shape')s.addShape(p.ShapeType[e.shape_kind||'rect'],{...r,objectName:e.id,fill:{color:z.fill},line:{color:z.fill,transparency:100}});
   else if(e.type==='line')s.addShape(p.ShapeType.line,{...r,objectName:e.id,line:{color:z.color,width:1.2,...(e.arrow_end?{endArrowType:'triangle'}:{})}});
   else if(e.type==='chart'){
    const compiled=compileChart(p,e.chart,r,e.id,page.background_color,spec.schema_version);
    s.addChart(compiled.type,compiled.data,compiled.options);
   }else if(e.type==='table'){
    const rows=[e.table.columns.map(text=>({text,options:{bold:true,color:'FFFFFF',fill:'117A7E'}})),...e.table.rows.map((row,i)=>row.map(text=>({text:String(text),options:{fill:i%2?'EBEFEB':'F5F3ED',color:'162E3B'}})))];
    const widths=spec.schema_version==='0.2'?e.table.columns.map(()=>r.w/e.table.columns.length):[3.05,2.25,6.45];
    s.addTable(rows,{...r,objectName:e.id,fontFace:'Microsoft YaHei',fontSize:z.font_size_pt||22,margin:[.14,.18,.14,.18],rowH:spec.schema_version==='0.2'?r.h/rows.length:.76,colW:widths,border:{type:'solid',pt:0,color:'F5F3ED'},autoPage:false});
   }else throw Error('Unsupported scene object');
  }
  s.addNotes(page.notes);
 }
 await p.writeFile({fileName:output});
}
main().catch(e=>{process.stderr.write(e.stack);process.exitCode=1});
