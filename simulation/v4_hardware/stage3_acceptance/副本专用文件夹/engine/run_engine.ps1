param([string]$CmdFile,[string]$LogFile,[string]$RawFile,[int]$TimeoutSeconds=900)
$ErrorActionPreference='Stop'
if(Test-Path $RawFile){throw ('Result exists; refusing to overwrite: ' + $RawFile)}
$app=New-Object -ComObject MultisimInterface.MultisimApp
$app.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$app.Connect()
try {
  $circuit=$app.NewFile()
  $sw=[Diagnostics.Stopwatch]::StartNew()
  $circuit.DoCommandLine($CmdFile,$LogFile)
  while($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    Start-Sleep -Milliseconds 500
    if((Test-Path $RawFile) -and $circuit.SimulationState -eq 0){
      if((Get-Item $RawFile).Length -gt 0){break}
    }
  }
  $r=[ordered]@{seconds=[math]::Round($sw.Elapsed.TotalSeconds,2);state=$circuit.SimulationState;error=$circuit.LastErrorMessage;rawExists=(Test-Path $RawFile);rawBytes=if(Test-Path $RawFile){(Get-Item $RawFile).Length}else{0}}
  $r | ConvertTo-Json -Compress
} finally {$app.Disconnect()}
