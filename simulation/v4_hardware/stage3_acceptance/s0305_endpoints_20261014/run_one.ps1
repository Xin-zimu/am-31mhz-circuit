param([Parameter(Mandatory=$true)][string]$Tag,[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Stop'
$runRoot='D:\ms_xsp\stage3_acceptance\s0305_endpoints_20261014'
if($Tag -notmatch '^[A-Za-z0-9_]+$'){throw 'Invalid run tag'}
if([IntPtr]::Size -ne 4){throw 'Use 32-bit Windows PowerShell for Multisim COM'}
$existing=@(Get-Process -Name multisim -ErrorAction SilentlyContinue)
if($existing.Count -gt 0){throw ('Preflight rejected: existing Multisim PIDs ' + ($existing.Id -join ','))}
$cmdPath=Join-Path $runRoot ($Tag+'.cmd')
$rawPath=Join-Path $runRoot ($Tag+'.raw')
$logPath=Join-Path $runRoot ($Tag+'.log')
$statusPath=Join-Path $PSScriptRoot ($Tag+'_status.json')
if(-not(Test-Path -LiteralPath $cmdPath)){throw 'Missing command file'}
foreach($p in @($rawPath,$logPath,$statusPath)){if(Test-Path -LiteralPath $p){throw ('Refusing overwrite: '+$p)}}
$record=[ordered]@{tag=$Tag;status='STARTED';entry='COM DoCommandLine source+tran engine';started_utc=[DateTime]::UtcNow.ToString('o');preflight_multisim_count=0;owned_pids=@();wall_seconds=0;last_error='';raw_path=$rawPath;raw_bytes=0;log_path=$logPath}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding UTF8
$app=$null
$owned=@()
$sw=[Diagnostics.Stopwatch]::StartNew()
try{
  $app=New-Object -ComObject MultisimInterface.MultisimApp
  $app.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $app.Connect()
  $owned=@(Get-Process -Name multisim -ErrorAction SilentlyContinue)
  $record.owned_pids=@($owned.Id)
  $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding UTF8
  $circuit=$app.NewFile()
  $circuit.DoCommandLine($cmdPath,$logPath)
  $settled=$false
  while($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    Start-Sleep -Milliseconds 500
    if($owned.Count -gt 0 -and @($owned | Where-Object {-not $_.HasExited}).Count -eq 0){
      throw 'Owned Multisim process exited before producing a complete result'
    }
    if(Test-Path -LiteralPath $rawPath){
      $length=(Get-Item -LiteralPath $rawPath).Length
      if($length -gt 0){
        Start-Sleep -Seconds 2
        if((Get-Item -LiteralPath $rawPath).Length -eq $length){$settled=$true;break}
      }
    }
    # Do not query COM properties while the engine is integrating. The first
    # retry ended in MSInterface.dll access violation after Multisim crashed.
    # Completion is determined from the final raw writer plus OS process state.
    if(Test-Path -LiteralPath $logPath){
      try{
        $logText=[IO.File]::ReadAllText($logPath)
        $engineError=[regex]::Match($logText,'(?m)^Error:.*$')
        if($engineError.Success){$record.last_error=$engineError.Value;break}
      }catch{}
    }
  }
  if($settled){try{$record.last_error=[string]$circuit.LastErrorMessage}catch{}}
  if($settled -and [string]::IsNullOrWhiteSpace($record.last_error)){$record.status='COMPLETED'}
  elseif($sw.Elapsed.TotalSeconds -ge $TimeoutSeconds){$record.status='TIMEOUT'}
  else{$record.status='FAILED'}
}
catch{$record.status='EXCEPTION';$record.last_error=$_.Exception.Message}
finally{
  $record.wall_seconds=[math]::Round($sw.Elapsed.TotalSeconds,2)
  if($app -and @($owned | Where-Object {-not $_.HasExited}).Count -gt 0){try{$app.Disconnect()}catch{}}
  # Only terminate processes created by this runner after the empty preflight.
  foreach($ownedProcess in $owned){if(-not $ownedProcess.HasExited){Stop-Process -Id $ownedProcess.Id -Force -ErrorAction SilentlyContinue}}
  Start-Sleep -Seconds 2
  if(Test-Path -LiteralPath $rawPath){$record.raw_bytes=(Get-Item -LiteralPath $rawPath).Length}
  if(Test-Path -LiteralPath $logPath){
    Copy-Item -LiteralPath $logPath -Destination (Join-Path $PSScriptRoot ($Tag+'.log'))
    $record.log_tail=@([IO.File]::ReadAllLines($logPath) | Select-Object -Last 8)
  }
  $record.finished_utc=[DateTime]::UtcNow.ToString('o')
  $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
$record | ConvertTo-Json -Depth 5 -Compress
if($record.status -ne 'COMPLETED'){exit 1}
