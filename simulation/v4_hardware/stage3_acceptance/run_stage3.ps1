param([string]$CmdFile,[string]$LogFile,[string]$DoneFile,[int]$TimeoutSeconds=600)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $DoneFile){throw 'Result exists; use a new run name to avoid stale completion.'}
$appStage3=New-Object -ComObject MultisimInterface.MultisimApp
$appStage3.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$appStage3.Connect()
try {
 $circuitStage3=$appStage3.NewFile()
 $timerStage3=[Diagnostics.Stopwatch]::StartNew()
 $circuitStage3.DoCommandLine($CmdFile,$LogFile)
 while($timerStage3.Elapsed.TotalSeconds -lt $TimeoutSeconds){
  Start-Sleep -Milliseconds 500
  if((Test-Path -LiteralPath $DoneFile) -and $circuitStage3.SimulationState -eq 0){
   if((Get-Item -LiteralPath $DoneFile).Length -gt 0){break}
  }
 }
 $resultStage3=[ordered]@{seconds=$timerStage3.Elapsed.TotalSeconds;state=$circuitStage3.SimulationState;error=$circuitStage3.LastErrorMessage;outputExists=(Test-Path -LiteralPath $DoneFile)}
 $resultStage3 | ConvertTo-Json
 if(-not $resultStage3.outputExists){throw 'No completed waveform output; inspect the log.'}
} finally {$appStage3.Disconnect()}
