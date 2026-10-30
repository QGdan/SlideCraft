param([Parameter(Mandatory=$true)][string]$Plan,[string]$Result='清理结果.json')
$ErrorActionPreference='Stop'
$cleanupPlan=Get-Content -LiteralPath $Plan -Raw -Encoding utf8 | ConvertFrom-Json
$runtimeRoot=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
if ([IO.Path]::GetFullPath($cleanupPlan.root).TrimEnd('\') -ne $runtimeRoot) { throw 'Plan root does not match this runtime' }
$rootPrefix=$runtimeRoot+'\'
if ([IO.Path]::GetFileName($Result) -ne $Result) { throw 'Result must be a plain filename' }
$output=Join-Path (Split-Path -Parent ([IO.Path]::GetFullPath($Plan))) $Result
if (Test-Path -LiteralPath $output) { throw 'Existing cleanup evidence must not be overwritten' }
$protectedPaths=@($runtimeRoot,(Join-Path $runtimeRoot '.venv'),(Join-Path $runtimeRoot '.mcp-venv'),(Join-Path $runtimeRoot 'node_modules'))
$records=@()
foreach ($entry in $cleanupPlan.candidates) {
  if (-not $entry.eligible) { continue }
  $target=[IO.Path]::GetFullPath([string]$entry.path).TrimEnd('\')
  if (-not $target.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase) -or $protectedPaths -contains $target) { throw 'Refused target outside disposable workspace scope' }
  if (-not (Test-Path -LiteralPath $target)) { $records+=@{path=$target;status='already-absent';bytes=0};continue }
  $item=Get-Item -LiteralPath $target -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refused reparse-point target' }
  $descendants=@(Get-ChildItem -LiteralPath $target -Recurse -Force)
  if (@($descendants | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'Refused nested reparse point' }
  $files=@($descendants | Where-Object { -not $_.PSIsContainer })
  $bytes=($files | Measure-Object -Property Length -Sum).Sum
  if ($null -eq $bytes) { $bytes=0 }
  if ($files.Count -ne $entry.files -or $bytes -ne $entry.bytes) { $records+=@{path=$target;status='skipped-changed-since-plan';bytes=0};continue }
  try {
    Remove-Item -LiteralPath $target -Recurse -Force
    if (Test-Path -LiteralPath $target) { throw 'Target retained after delete' }
    $records+=@{path=$target;status='deleted';bytes=$bytes;files=$files.Count}
  } catch { $records+=@{path=$target;status='failed-or-partial';error=$_.Exception.Message;bytes=0} }
}
@{root=$runtimeRoot;records=$records;deleted_bytes=($records | Where-Object {$_.status -eq 'deleted'} | Measure-Object -Property bytes -Sum).Sum} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $output -Encoding utf8
Get-Content -LiteralPath $output -Raw -Encoding utf8
