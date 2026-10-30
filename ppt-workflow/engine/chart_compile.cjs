// Original compiler implementation; explicit supported subset, no image fallback.
const caps=require('./capabilities.json');
function compileChart(p,chart,rect,id,background,version='0.1'){
 const extended=version==='0.2',kind=chart.kind,values=chart.series.flatMap(s=>s.values),n=chart.categories.length;
 if(!caps.chart_kinds.includes(kind))throw Error(`Unsupported chart kind: ${kind}`);
 if(!extended&&(kind!=='bar'||chart.options||chart.semantics))throw Error('Extended charts require schema_version 0.2');
 if(!values.length||values.some(v=>!Number.isFinite(v)))throw Error('Finite chart values required');
 if(chart.series.some(s=>s.values.length!==n))throw Error('Chart categories/values length mismatch');
 const c=chart.options||{},sem=chart.semantics||{};
 if(extended){
  if(n>caps.max_categories||chart.series.length>caps.max_series)throw Error('Chart capacity exceeded');
  if(!sem.reason||(kind==='line'?(sem.task!=='trend'||sem.category_order!=='chronological'):sem.task!=='comparison'))throw Error('Unsupported chart semantics');
  if(chart.unit==='%'&&values.some(v=>v<0||v>100))throw Error('Percentages use 0–100');
  if(c.emphasize_categories?.some(x=>!chart.categories.includes(x)))throw Error('Unknown emphasis category');
  if(c.emphasize_series?.some(x=>!chart.series.some(s=>s.name===x)))throw Error('Unknown emphasis series');
  if(c.emphasize_categories?.length&&(kind==='line'||chart.series.length!==1))throw Error('Category emphasis requires one bar/column series');
  if(c.emphasize_categories?.length&&c.emphasize_series?.length)throw Error('Conflicting emphasis modes');
  if(c.presentation_preset){
   const presets={'focus-comparison':['bar',6,1],'series-comparison':['column',4,2],'focus-trend':['line',8,2]};
   const spec=presets[c.presentation_preset];
   if(!spec||kind!==spec[0]||n<2||n>spec[1]||chart.series.length>spec[2])throw Error('Chart presentation preset capacity/type mismatch');
   if(c.presentation_preset==='focus-comparison'&&c.emphasize_categories?.length!==1)throw Error('Focused comparison requires one emphasis category');
   if(c.presentation_preset==='series-comparison'&&chart.series.length!==2)throw Error('Series comparison requires two series');
   if(c.presentation_preset==='focus-trend'&&chart.categories.some((x,i,a)=>!/^\d{4}-(0[1-9]|1[0-2])$/.test(x)||x.slice(0,4)==='0000'||(i>0&&x<=a[i-1])))throw Error('Trend requires ascending ISO months');
  }
 }
 const min=c.axis_min??(extended?Math.floor(Math.min(0,...values)*1.15):0),max=c.axis_max??(extended&&chart.unit==='%'?100:Math.max(1,Math.ceil(Math.max(0,...values)*1.15)));
 if(min>=max||min>Math.min(0,...values)||max<Math.max(...values))throw Error('Axis clips data or zero');
 const accent=c.colors?.accent||'117A7E',muted=c.colors?.muted||'ABB8BC',ink=c.colors?.ink||'162E3B',font=c.font_face||'Microsoft YaHei';
 let colors=extended?(c.colors?.series||(c.colors?[accent]:['117A7E','3159AD','9E5B32','7455A4'])):['9AB1B3','117A7E'];
 if(c.emphasize_categories?.length)colors=chart.categories.map(label=>c.emphasize_categories.includes(label)?accent:muted);
 else if(c.emphasize_series?.length)colors=chart.series.map(s=>c.emphasize_series.includes(s.name)?accent:muted);
 else if(chart.series.length===1&&kind!=='line')colors=Array.from({length:n},(_,i)=>extended?accent:colors[i%colors.length]);
 const options={...rect,objectName:id,barDir:kind==='column'?'col':'bar',barGapWidthPct:105,chartColors:colors,
  showTitle:false,showLegend:c.show_legend??(extended&&chart.series.length>1),
  showValue:!(extended&&kind==='line'&&chart.series.length>1),showCatName:false,showSerName:false,dataLabelPosition:kind==='line'?'t':'outEnd',
  dataLabelFontFace:font,dataLabelFontSize:extended?18:24,dataLabelFontBold:true,dataLabelColor:ink,
  dataLabelFormatCode:c.label_format??(extended?(chart.unit==='%'?'0.00"%"':'General'):'0'),
  catAxisLabelFontFace:font,catAxisLabelFontSize:extended?16:20,catAxisLabelColor:ink,catAxisLineShow:false,
  valAxisLabelFontFace:font,valAxisLabelColor:ink,legendFontFace:font,legendColor:ink,
  valAxisMinVal:min,valAxisMaxVal:max,valAxisHidden:!(c.show_axis??extended),
  valAxisLabelFormatCode:chart.unit==='%'?'0"%"':'General',valGridLine:{style:'none'},catGridLine:{style:'none'},
  chartArea:{fill:{color:background},border:{color:background,pt:0}},plotArea:{fill:{color:background},border:{color:background,pt:0}}};
 if(extended&&c.presentation_preset){
  Object.assign(options,{catAxisLabelFontSize:14,valAxisLabelFontSize:14,dataLabelFontSize:16,legendFontSize:16,legendPos:'b',
   showLegend:chart.series.length>1,valAxisHidden:false,catAxisLabelRotate:0,
   valGridLine:kind==='bar'?{style:'none'}:{style:'solid',color:'D6DDDF',size:.5}});
  if(kind==='line')Object.assign(options,{lineSize:2.75,lineDataSymbol:'circle',lineDataSymbolSize:5,showValue:false});
  if(kind==='bar')Object.assign(options,{catAxisOrientation:'maxMin',catAxisCrossesAt:'max',valAxisLabelPos:'nextTo'});
 }
 return {type:kind==='line'?p.ChartType.line:p.ChartType.bar,
  data:chart.series.map(s=>({name:s.name,labels:chart.categories,values:s.values})),options};
}
module.exports={compileChart};
