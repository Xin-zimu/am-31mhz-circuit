# Single-call run: one RunSimulation covering the whole window, no chunk pausing.
param([string]$Project,[string]$Tag,[double]$RunS=2e-5,[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
$sw=[Diagnostics.Stopwatch]::StartNew()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('TAG=' + $Tag + ' state=' + $c.SimulationState)
  $c.RunSimulation($RunS, $true)
  # poll until it settles
  while($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    Start-Sleep -Milliseconds 500
    $st=$c.SimulationState; $er=$c.LastErrorMessage
    if($er -and $er.Length -gt 0){ Write-Output ('*** ERROR msg=' + $er); break }
    if($st -eq 2){ Write-Output ('*** PAUSED/COMPLETE at requested ' + $RunS.ToString('E3') + ' s'); break }
    if($st -eq 0){ Write-Output ('*** STOPPED state=0'); break }
  }
  Write-Output ('final state=' + $c.SimulationState + ' wall=' + [math]::Round($sw.Elapsed.TotalSeconds,1) + 's')
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'