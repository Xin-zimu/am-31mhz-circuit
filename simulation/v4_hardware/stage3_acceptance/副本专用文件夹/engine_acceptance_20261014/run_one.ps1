param([Parameter(Mandatory=$true)][string]$Tag,[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Stop'
$runRoot='D:\ms_xsp\stage3_acceptance\s0304_acceptance_20261014'
if($Tag -notmatch '^[A-Za-z0-9_]+$'){throw 'Invalid run tag'}
$cmdPath   = Join-Path $runRoot ($Tag+'.cmd')
$logPath   = Join-Path $runRoot ($Tag+'.log')
$rawPath   = Join-Path $runRoot ($Tag+'.raw')
$statusPath= Join-Path $PSScriptRoot ($Tag+'_status.json')
$logCopy   = Join-Path $PSScriptRoot ($Tag+'.log')

if(-not (Test-Path -LiteralPath $cmdPath)){throw "Missing command file: $cmdPath"}
if((Test-Path -LiteralPath $rawPath) -and (Get-Item -LiteralPath $rawPath).Length -gt 0){
  throw ('Refusing to overwrite existing result: ' + $rawPath)
}
Remove-Item -LiteralPath $rawPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue

$record=[ordered]@{
  tag=$Tag
  status='STARTED'
  entry='COM DoCommandLine; source + tran command engine. No native GUI pass claimed.'
  wall_seconds=0.0
  state=$null
  last_error=''
  polls=0
  raw_exists=$false
  raw_bytes=0
  log_path=$logPath
  raw_path=$rawPath
  log_tail=@()
}

$app=$null
$sw=[Diagnostics.Stopwatch]::StartNew()
try{
  $app=New-Object -ComObject MultisimInterface.MultisimApp
  $app.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $app.Connect()
  $circuit=$app.NewFile()

  # DoCommandLine returns as soon as the command is queued on this host; the
  # analysis keeps running in the background. The .raw file is produced by the
  # FINAL command of the script (write-and-destroy-iplot), so a non-empty .raw
  # is the completion signal. Poll instead of assuming synchronous return.
  $circuit.DoCommandLine($cmdPath,$logPath)

  $settled=$false
  while($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    Start-Sleep -Milliseconds 500
    $record.polls=[int]$record.polls+1
    if(Test-Path -LiteralPath $rawPath){
      $len=(Get-Item -LiteralPath $rawPath).Length
      if($len -gt 0){ $record.raw_bytes=$len; $settled=$true; break }
    }
    $st=$null
    try{ $st=$circuit.SimulationState }catch{}
    $record.state=$st
    if($st -eq 0 -or $st -eq 2){
      # Give the writer a moment, then take a final look.
      Start-Sleep -Milliseconds 1000
      if(Test-Path -LiteralPath $rawPath){
        $len=(Get-Item -LiteralPath $rawPath).Length
        if($len -gt 0){ $record.raw_bytes=$len; $settled=$true }
      }
      break
    }
  }

  try{ $record.last_error=$circuit.LastErrorMessage }catch{}
  $record.wall_seconds=[math]::Round($sw.Elapsed.TotalSeconds,2)

  if($settled -and $record.raw_bytes -gt 0){
    $record.status='COMPLETED'
  } elseif($sw.Elapsed.TotalSeconds -ge $TimeoutSeconds){
    $record.status='TIMEOUT'
  } else {
    $record.status='NO-RESULT'
  }
}
catch{
  $record.status='EXCEPTION'
  $record.last_error=$_.Exception.Message
  $record.wall_seconds=[math]::Round($sw.Elapsed.TotalSeconds,2)
}
finally{
  if($app){ try{$app.Disconnect()}catch{} }
  # Log copy is advisory only: the file may still be held by Multisim.
  if(Test-Path -LiteralPath $logPath){
    try{ Copy-Item -LiteralPath $logPath -Destination $logCopy -Force -ErrorAction Stop }
    catch{ $record.log_copy_error=$_.Exception.Message }
    try{ $record.log_tail=@(Get-Content -LiteralPath $logPath -Tail 6 -ErrorAction Stop) }catch{}
  }
  $record.raw_exists=Test-Path -LiteralPath $rawPath
  $record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

$record | ConvertTo-Json -Depth 4 -Compress
if($record.status -ne 'COMPLETED'){ exit 1 }
