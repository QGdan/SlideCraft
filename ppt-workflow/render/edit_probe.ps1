param([Parameter(Mandatory=$true)][string]$Request,[Parameter(Mandatory=$true)][string]$Report)
$ErrorActionPreference='Stop'
$q=Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json
$r=@{status='failed';error=$null;operations=@()};$app=$null;$pres=$null;$owned=$false
function Release-Com($v){if($null -ne $v){[Runtime.InteropServices.Marshal]::ReleaseComObject($v)|Out-Null}}
try {
  if(@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0){throw 'Existing user PowerPoint process; probe refused.'}
  if(Test-Path -LiteralPath $q.output){throw 'Fresh probe output required.'}
  $app=New-Object -ComObject PowerPoint.Application
  $owned=($app.Presentations.Count -eq 0)
  if(-not $owned){throw 'Existing presentations; probe refused.'}
  $r.version=[string]$app.Version;$r.build=[string]$app.Build
  $pres=$app.Presentations.Open($q.input,$false,$false,$false)
  foreach($op in $q.operations){
    $slide=$null;$shapes=$null;$shape=$null;$table=$null;$cell=$null;$cellShape=$null;$frame=$null;$range=$null
    try{
      $slide=$pres.Slides.Item([int]$op.slide);$shapes=$slide.Shapes;$shape=$shapes.Item([string]$op.name)
      if($op.kind -eq 'chart-resize'){
        if($shape.HasChart -ne -1){throw 'Expected native chart.'}
        $old=[double]$shape.Width;$shape.Width=$old-[double]$op.delta_pt
        $r.operations+=@{name=$op.name;kind=$op.kind;before=$old;after=[double]$shape.Width}
      }elseif($op.kind -eq 'table-cell'){
        if($shape.HasTable -ne -1){throw 'Expected native table.'}
        $table=$shape.Table;$cell=$table.Cell([int]$op.row,[int]$op.col);$cellShape=$cell.Shape;$frame=$cellShape.TextFrame;$range=$frame.TextRange
        $old=[string]$range.Text;$range.Text=[string]$op.text
        $r.operations+=@{name=$op.name;kind=$op.kind;before=$old;after=[string]$range.Text}
      }elseif($op.kind -eq 'text'){
        $frame=$shape.TextFrame;$range=$frame.TextRange;$old=[string]$range.Text;$range.Text=[string]$op.text
        $r.operations+=@{name=$op.name;kind=$op.kind;before=$old;after=[string]$range.Text}
      }else{throw 'Unsupported edit operation.'}
    }finally{Release-Com $range;Release-Com $frame;Release-Com $cellShape;Release-Com $cell;Release-Com $table;Release-Com $shape;Release-Com $shapes;Release-Com $slide}
  }
  $pres.SaveAs([string]$q.output,24);$pres.Close();Release-Com $pres;$pres=$null
  $pres=$app.Presentations.Open([string]$q.output,$true,$false,$false)
  $r.reopenedSlideCount=[int]$pres.Slides.Count
  $r.status='saved-and-reopened'
}catch{$r.error=$_.Exception.Message}
finally{
  if($null -ne $pres){try{$pres.Close()}catch{$r.cleanupError=$_.Exception.Message};Release-Com $pres}
  if($null -ne $app){if($owned){try{if($app.Presentations.Count -eq 0){$app.Quit()}else{$r.cleanupError='Unexpected other presentations opened; application retained.'}}catch{$r.cleanupError=$_.Exception.Message}};Release-Com $app}
  $r.cleanupCompleted=($null -eq $r.cleanupError)
  [GC]::Collect();[GC]::WaitForPendingFinalizers()
  $r|ConvertTo-Json -Depth 16|Set-Content -LiteralPath $Report -Encoding UTF8
}
if($r.status -eq 'saved-and-reopened' -and $r.cleanupCompleted){exit 0};exit 2
