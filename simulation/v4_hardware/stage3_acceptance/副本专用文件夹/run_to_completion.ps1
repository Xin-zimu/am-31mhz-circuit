# Unambiguous driver: one blocking call that runs the analysis to its own TSTOP.
param([string]$Project,[string]$Tag,[double]$RunS=1.0,[int]$TimeoutSeconds=3600)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
$sw=[Diagnostics.Stopwatch]::StartNew()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('TAG=' + $Tag + ' name=' + $c.CircuitName + ' state=' + $c.SimulationState)
  $runSw=[Diagnostics.Stopwatch]::StartNew()
  try { $c.RunSimulation($RunS, $false) } catch { Write-Output ('RUN-EXC ' + $_.Exception.Message) }
  $runWall=[math]::Round($runSw.Elapsed.TotalSeconds,1)
  Start-Sleep -Seconds 2
  $st=$c.SimulationState; $er=$c.LastErrorMessage
  Write-Output ('RESULT tag=' + $Tag + ' state=' + $st + ' err=' + $er + ' runWall=' + $runWall + 's')
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'