# Drive the project's OWN transient analysis, waiting for the paused/stopped state
# between chunks so the solver is never re-entered while running.
param([string]$Project,[string]$Tag,[double]$ChunkS=1e-7,[double]$StopS=2e-5,[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
$sw=[Diagnostics.Stopwatch]::StartNew()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('TAG=' + $Tag + ' name=' + $c.CircuitName + ' state=' + $c.SimulationState)
  $simT=0.0; $fail=$null; $n=0
  while($simT -lt $StopS -and $sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    $n++
    try { $c.RunSimulation($ChunkS, $true) }
    catch { Write-Output ('  chunk ' + $n + ' EXC ' + $_.Exception.Message) }
    # wait for the chunk to actually pause or stop
    $w=[Diagnostics.Stopwatch]::StartNew()
    while($w.Elapsed.TotalSeconds -lt 120){
      Start-Sleep -Milliseconds 200
      $st=$c.SimulationState
      if($st -eq 2 -or $st -eq 0){ break }
    }
    $st=$c.SimulationState; $er=$c.LastErrorMessage
    if($er -and $er.Length -gt 0){ $fail=$simT; Write-Output ('*** FAILED near t=' + $simT.ToString('E3') + ' s  msg=' + $er); break }
    if($st -eq 0 -and $simT -gt 0){ Write-Output ('*** solver stopped at t~' + $simT.ToString('E3')); break }
    $simT += $ChunkS
    if($n % 20 -eq 0){ Write-Output ('  .. t~' + $simT.ToString('E3') + ' wall=' + [math]::Round($sw.Elapsed.TotalSeconds,0) + 's') }
  }
  if($null -eq $fail){ Write-Output ('REACHED t~' + $simT.ToString('E3') + ' s without error; state=' + $c.SimulationState) }
  Write-Output ('wall=' + [math]::Round($sw.Elapsed.TotalSeconds,1) + 's chunks=' + $n)
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'