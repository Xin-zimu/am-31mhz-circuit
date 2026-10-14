param([string]$CmdFile,[string]$LogFile,[string]$DoneFile)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.NewFile()
 $c.DoCommandLine($CmdFile,$LogFile)
 $watch=[Diagnostics.Stopwatch]::StartNew()
 while($watch.Elapsed.TotalSeconds -lt 180){
   Start-Sleep -Milliseconds 500
   if(Test-Path -LiteralPath $DoneFile){
      $len=(Get-Item -LiteralPath $DoneFile).Length
      if($len -gt 0 -and $c.SimulationState -eq 0){break}
   }
 }
 Write-Output ('seconds='+$watch.Elapsed.TotalSeconds+' state='+$c.SimulationState+' error='+$c.LastErrorMessage)
} finally {$a.Disconnect()}
