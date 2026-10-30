/* P2 native renderer; all scene coordinates and stable IDs are owned by spec. */
const fs = require('fs');
const pptxgen = require('pptxgenjs');
async function build() {
  const [specPath, themePath, output] = process.argv.slice(2);
  if (!output || fs.existsSync(output)) throw Error('Fresh output filename required');
  const spec = JSON.parse(fs.readFileSync(specPath,'utf8'));
  const t = JSON.parse(fs.readFileSync(themePath,'utf8'));
  const pptx = new pptxgen();
  pptx.defineLayout({name:'SCENE',width:spec.canvas.width,height:spec.canvas.height});
  pptx.layout='SCENE'; pptx.author='PPT workflow'; pptx.subject='明确标注的方案与示意数据';
  pptx.title='教学报告自动化试点方案'; pptx.lang='zh-CN';
  pptx.theme={headFontFace:t.font,bodyFontFace:t.font,lang:'zh-CN'};
  for (const page of spec.slides) {
    const s=pptx.addSlide(); s.background={color:t.bg};
    for (const e of page.elements) {
      const z=e.style||{}, r=e.rect;
      const o={...r,objectName:e.id,fontFace:z.font_face||t.font,fontSize:z.font_size_pt||t.body,
        color:z.color||t.ink,bold:!!z.bold,align:z.align||'left',margin:0,breakLine:false,
        valign:'mid',transparency:0};
      if(e.type==='text') s.addText(e.text,{...o,paraSpaceAfterPt:0,wrap:true});
      else if(e.type==='shape') s.addShape(pptx.ShapeType.rect,{...o,fill:{color:z.fill||t.light},line:{color:z.color||t.accent,width:1}});
      else if(e.type==='line') s.addShape(pptx.ShapeType.line,{...o,line:{color:z.color||t.rule,width:1.1,...(e.arrow_end?{endArrowType:'triangle'}:{})}});
      else if(e.type==='image') s.addImage({...r,path:e.asset_path,objectName:e.id});
      else if(e.type==='chart') {
        if(!['bar','column','line','pie'].includes(e.chart.kind)) throw Error('Unsupported P2 chart kind');
        const c=e.chart;
        const options={...r,objectName:e.id,chartColors:[t.accent,t.ink],showTitle:false,showLegend:false,
          showValue:true,showCatName:false,showSerName:false,dataLabelPosition:c.kind==='line'?'t':'outEnd',
          dataLabelColor:t.ink,dataLabelFontFace:t.font,dataLabelFontSize:t.chart_label,
          catAxisLabelFontFace:t.font,catAxisLabelFontSize:t.chart_label,catAxisLabelColor:t.ink,
          valAxisLabelFontFace:t.font,valAxisLabelFontSize:t.chart_label,valAxisLabelColor:t.muted,
          valAxisMinVal:0,valAxisMaxVal:45,valAxisMajorUnit:10,valAxisLabelFormatCode:'0',
          valGridLine:{color:t.rule,width:.5},catAxisLineColor:t.rule,valAxisLineColor:t.rule,
          showBorder:false,showMarker:true,
          chartArea:{fill:{color:t.bg},border:{color:t.bg,pt:0}},
          plotArea:{fill:{color:t.bg},border:{color:t.bg,pt:0}},barDir:c.kind==='bar'?'bar':'col',barGapWidthPct:100,
          showValue:true};
        s.addChart(c.kind==='column'?pptx.ChartType.bar:pptx.ChartType[c.kind],c.series.map(v=>({name:v.name,labels:c.categories,values:v.values})),options);
      } else if(e.type==='table') {
        const rows=[e.table.columns.map(text=>({text,options:{bold:true,color:t.bg,fill:t.accent}})),
          ...e.table.rows.map(row=>row.map(v=>({text:v===null?'':String(v),options:{color:t.ink,fill:t.bg}})))];
        s.addTable(rows,{...r,objectName:e.id,fontFace:t.font,fontSize:20,color:t.ink,
          border:{type:'solid',pt:.6,color:t.rule},margin:[.12,.14,.12,.14],
          colW:[3.15,2.05,6.45],rowH:.74,autoPage:false,verbose:false});
      } else throw Error(`Unknown scene type ${e.type}`);
    }
    s.addNotes(page.notes);
  }
  await pptx.writeFile({fileName:output});
}
build().catch(e=>{process.stderr.write(String(e.stack));process.exitCode=1});
