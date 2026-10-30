# P0-only PowerPoint probe. Production renderer reliability is a P1 task.
param(
  [Parameter(Mandatory=$true)][string]$Pptx,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$Report
)
$ErrorActionPreference = 'Stop'
$result = @{status='unverified'; renderer='PowerPoint COM'; slides=@(); error=$null}
$app = $null
$pres = $null
$slides = $null
$ownedApplication = $false
$started = [Diagnostics.Stopwatch]::StartNew()
function Get-LocalSha256([string]$Path) {
  $stream = [IO.File]::OpenRead($Path)
  $algorithm = [Security.Cryptography.SHA256]::Create()
  try {
    return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant()
  } finally {
    $algorithm.Dispose()
    $stream.Dispose()
  }
}
try {
  $before = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue)
  if ($before.Count -gt 0) {
    throw 'Existing PowerPoint process detected; P0 does not take ownership of user sessions.'
  }
  if (Test-Path -LiteralPath $OutDir) {
    throw 'Output directory already exists; use a fresh P0 run directory.'
  }
  $deckPath = (Resolve-Path -LiteralPath $Pptx).Path
  $app = New-Object -ComObject PowerPoint.Application
  $ownedApplication = ($app.Presentations.Count -eq 0)
  if (-not $ownedApplication) {
    throw 'PowerPoint application has existing presentations; leave the session untouched.'
  }
  $result.officeVersion = [string]$app.Version
  $result.officeBuild = [string]$app.Build
  $result.inputSha256 = Get-LocalSha256 $deckPath
  New-Item -ItemType Directory -Path $OutDir | Out-Null
  $outputPath = (Resolve-Path -LiteralPath $OutDir).Path
  $pres = $app.Presentations.Open($deckPath, $true, $false, $false)
  $slides = $pres.Slides
  $count = $slides.Count
  if ($count -ne 10) { throw "Expected ten baseline slides, got $count." }
  for ($i=1; $i -le $count; $i++) {
    $slide = $null
    try {
      $slide = $slides.Item($i)
      $file = Join-Path $outputPath ('slide-{0:d2}.png' -f $i)
      $slide.Export($file, 'PNG', 1600, 900)
      if (-not (Test-Path -LiteralPath $file)) { throw "Missing exported slide $i." }
      $result.slides += @{slide=$i; path=$file; sha256=(Get-LocalSha256 $file)}
    } finally {
      if ($null -ne $slide) { [Runtime.InteropServices.Marshal]::ReleaseComObject($slide) | Out-Null }
    }
  }
  $result.status = 'exported_pending_image_validation'
} catch {
  $result.error = $_.Exception.Message
} finally {
  if ($null -ne $slides) { [Runtime.InteropServices.Marshal]::ReleaseComObject($slides) | Out-Null }
  if ($null -ne $pres) {
    try { $pres.Close() } catch { $result.cleanupError = $_.Exception.Message }
    [Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
  }
  if ($null -ne $app) {
    if ($ownedApplication) {
      try {
        if ($app.Presentations.Count -eq 0) { $app.Quit() }
        else { $result.cleanupNote = 'Other presentations are open; application kept running.' }
      } catch { $result.cleanupError = $_.Exception.Message }
    }
    [Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
  }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
  $result.elapsedSeconds = [Math]::Round($started.Elapsed.TotalSeconds,3)
  $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Report -Encoding UTF8
}
if ($result.status -eq 'exported_pending_image_validation') {
  Write-Output 'P0 PowerPoint export finished; verify the image manifest next.'
  exit 0
}
Write-Output ("P0 rendering unverified: " + $result.error)
exit 2
