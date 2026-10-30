# Read-only direct COM activation; shared WPS is never quit.
param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output=[IO.Path]::GetFullPath($Out);$prefix=(Join-Path $projectRoot 'runs')+[IO.Path]::DirectorySeparatorChar
if (-not $output.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $output)) { throw 'Fresh output subdirectory inside runs required' }
[IO.Directory]::CreateDirectory($output) | Out-Null
$result=@{status='failed';route='direct-powershell';application_quit_called=$false;document_modified=$false};$app=$null
try {
 $app=New-Object -ComObject KWPP.Application
 $result.version=[string]$app.Version;$result.presentations=[int]$app.Presentations.Count;$result.status='connected'
} catch { $result.error=$_.Exception.Message }
finally {
 if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
 [GC]::Collect();[GC]::WaitForPendingFinalizers()
 $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'wps-direct-connection.json') -Encoding utf8
}
$result | ConvertTo-Json
if ($result.status -ne 'connected') { exit 2 }
