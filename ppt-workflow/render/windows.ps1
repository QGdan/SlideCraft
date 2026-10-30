param(
  [Parameter(Mandatory=$true)][string]$Pptx,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$Report,
  [int]$Width=1600,
  [int]$Height=900
)
$ErrorActionPreference='Stop'
$result=@{status='failed'; renderer='PowerPoint COM'; error=$null; textBounds=@()}
$app=$null; $pres=$null; $slides=$null; $owned=$false
function Get-Sha([string]$Path) {
  $stream=[IO.File]::OpenRead($Path); $alg=[Security.Cryptography.SHA256]::Create()
  try { return [BitConverter]::ToString($alg.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
  finally { $stream.Dispose(); $alg.Dispose() }
}
function Release-Com($value) {
  if ($null -ne $value) { [Runtime.InteropServices.Marshal]::ReleaseComObject($value) | Out-Null }
}
function Record-Text($shape,[string]$id) {
  $frame=$null; $range=$null
  try {
    if ($shape.HasTextFrame -eq -1) {
      $frame=$shape.TextFrame
      if ($frame.HasText -eq -1) {
        $range=$frame.TextRange
        $result.textBounds += @{elementId=$id; text=[string]$range.Text; rawBoundPt=@([double]$range.BoundLeft,[double]$range.BoundTop,[double]$range.BoundWidth,[double]$range.BoundHeight); rawFramePt=@([double]$shape.Left,[double]$shape.Top,[double]$shape.Width,[double]$shape.Height); coordinateNote='Raw target-engine points; transformed groups need coordinate interpretation.'}
      }
    }
  } catch { $result.boundsWarnings += @($id+': '+$_.Exception.Message) }
  finally { Release-Com $range; Release-Com $frame }
}
function Walk-Shapes($shapes,[string]$prefix) {
  for ($j=1; $j -le $shapes.Count; $j++) {
    $shape=$null; $children=$null
    try {
      $shape=$shapes.Item($j); $id=$prefix+'/shape-'+[string]$shape.Id
      if ($shape.Type -eq 6) {
        $children=$shape.GroupItems
        Walk-Shapes $children $id
      } else { Record-Text $shape $id }
    } finally { Release-Com $children; Release-Com $shape }
  }
}
try {
  if (@(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0) { throw 'Existing PowerPoint process detected; user session not taken over.' }
  if (Test-Path -LiteralPath $OutDir) { throw 'Slide output directory already exists.' }
  $inputPath=(Resolve-Path -LiteralPath $Pptx).Path
  $result.inputSha256=Get-Sha $inputPath
  $app=New-Object -ComObject PowerPoint.Application
  $owned=($app.Presentations.Count -eq 0)
  if (-not $owned) { throw 'Application has existing presentations; leave it untouched.' }
  $result.version=[string]$app.Version; $result.build=[string]$app.Build
  New-Item -ItemType Directory -Path $OutDir | Out-Null
  $outputPath=(Resolve-Path -LiteralPath $OutDir).Path
  $pres=$app.Presentations.Open($inputPath,$true,$false,$false)
  $slides=$pres.Slides; $result.slideCount=$slides.Count
  if ($slides.Count -le 0) { throw 'Empty presentation.' }
  for ($i=1; $i -le $slides.Count; $i++) {
    $slide=$null; $shapes=$null
    try {
      $slide=$slides.Item($i)
      $slide.Export((Join-Path $outputPath ('slide-{0:d3}.png' -f $i)),'PNG',$Width,$Height)
      $shapes=$slide.Shapes
      Walk-Shapes $shapes ('slide-'+$i)
    } finally { Release-Com $shapes; Release-Com $slide }
  }
  $result.status='exported'
} catch { $result.error=$_.Exception.Message }
finally {
  Release-Com $slides
  if ($null -ne $pres) {
    try { $pres.Close() } catch { $result.cleanupError=$_.Exception.Message }
    Release-Com $pres
  }
  if ($null -ne $app) {
    if ($owned) {
      try {
        if ($app.Presentations.Count -eq 0) { $app.Quit() }
        else { $result.cleanupNote='Other presentations opened during run; application retained.' }
      } catch { $result.cleanupError=$_.Exception.Message }
    }
    Release-Com $app
  }
  $result.cleanupCompleted=($null -eq $result.cleanupError)
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
  $result | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $Report -Encoding UTF8
}
if ($result.status -eq 'exported' -and -not $result.cleanupError) { exit 0 }
exit 2
