# Run this entry directly in PowerShell 7 when the Python -> Office launch chain fails.
param([Parameter(Mandatory=$true)][string]$Pptx,[Parameter(Mandatory=$true)][string]$Out,[int]$Timeout=60,[int]$Width=1600,[int]$Height=900)
$ErrorActionPreference='Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Direct Office route requires PowerShell 7.' }
if ($Timeout -lt 1 -or $Timeout -gt 120 -or $Width -le 0 -or $Height -le 0) { throw 'Invalid bounded timeout or image size' }
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output=[IO.Path]::GetFullPath($Out);$inputFile=(Resolve-Path -LiteralPath $Pptx).Path
$runsPrefix=(Join-Path $projectRoot 'runs')+[IO.Path]::DirectorySeparatorChar
if (-not $output.StartsWith($runsPrefix,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $output)) { throw 'Fresh output subdirectory inside project runs required' }
$lock=Join-Path $projectRoot 'runs/.powerpoint-worker-lock'
$ownsLock=$false;$process=$null;$workerStarted=$false;$cleanupVerified=$false;$result=@{returncode=$null;timed_out=$false;launch_route='direct-powershell'}
try {
 New-Item -ItemType Directory -Path $lock -ErrorAction Stop | Out-Null;$ownsLock=$true
 @{pid=$PID;route='direct-powershell';started_at=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $lock 'owner.json') -Encoding utf8
 [IO.Directory]::CreateDirectory($output) | Out-Null
 $info=[Diagnostics.ProcessStartInfo]::new()
 $info.FileName=Join-Path $PSHOME 'pwsh.exe'
 $info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
 $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
 $arguments=@('-NoProfile','-File',(Join-Path $projectRoot 'render/windows.ps1'),'-Pptx',$inputFile,'-OutDir',(Join-Path $output 'slides'),'-Report',(Join-Path $output 'powerpoint-worker.json'),'-Width',[string]$Width,'-Height',[string]$Height)
 foreach ($argument in $arguments) { $info.ArgumentList.Add($argument) }
 $result.command=@($info.FileName)+$arguments
 $process=[Diagnostics.Process]::new();$process.StartInfo=$info;[void]$process.Start();$workerStarted=$true
 $readOut=$process.StandardOutput.ReadToEndAsync();$readError=$process.StandardError.ReadToEndAsync()
 if (-not $process.WaitForExit($Timeout*1000)) {
  $result.timed_out=$true;$process.Kill();[void]$process.WaitForExit(5000)
  @{reason='Direct worker timeout; COM ownership unknown';output=$output} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $lock 'quarantine.json') -Encoding utf8
 }
 if ($process.HasExited) { $result.returncode=$process.ExitCode }
 $result.stdout=if ($readOut.IsCompleted) { $readOut.GetAwaiter().GetResult() } else { '[output incomplete]' }
 $result.stderr=if ($readError.IsCompleted) { $readError.GetAwaiter().GetResult() } else { '[output incomplete]' }
 $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'process.json') -Encoding utf8
 $workerPath=Join-Path $output 'powerpoint-worker.json'
 if (-not (Test-Path -LiteralPath $workerPath)) {
  @{reason='No direct worker cleanup evidence';output=$output} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $lock 'quarantine.json') -Encoding utf8
  throw 'No worker evidence; lock quarantined'
 }
 $worker=Get-Content -LiteralPath $workerPath -Raw | ConvertFrom-Json
 if ($worker.cleanupCompleted -ne $true -or $worker.cleanupError) {
  @{reason='Direct worker cleanup uncertain';output=$output} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $lock 'quarantine.json') -Encoding utf8
  throw 'Worker cleanup uncertain; lock quarantined'
 }
 $cleanupVerified=$true
 if ($result.timed_out -or $result.returncode -ne 0) { throw ('Direct worker failed: '+$worker.error) }
 & (Join-Path $projectRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'verify_direct_render.py') --pptx $inputFile --out $output --width $Width --height $Height
 if ($LASTEXITCODE -ne 0) { throw 'Direct render verification failed' }
} finally {
 if ($ownsLock -and $workerStarted -and -not $cleanupVerified) {
  @{reason='Direct worker exited or interrupted without verified cleanup';output=$output} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $lock 'quarantine.json') -Encoding utf8
 }
 if ($null -ne $process) { $process.Dispose() }
 if ($ownsLock -and -not (Test-Path -LiteralPath (Join-Path $lock 'quarantine.json'))) {
  Remove-Item -LiteralPath (Join-Path $lock 'owner.json') -ErrorAction SilentlyContinue
  # Nonrecursive removal preserves any unexpected files rather than deleting them.
  Remove-Item -LiteralPath $lock -ErrorAction Stop
 }
}
