# Fine bracket: drive the failing project in 5 ns chunks, capture error text and stop time.
param([string]$Project,[string]$Tag,[double]$ChunkS=5e-9,[double]$StopS=1e-6,[int]$TimeoutSeconds=900)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
$sw=[Diagnostics.Stopwatch]::StartNew()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('TAG=' + $Tag + ' name=' + $c.CircuitName)
  $simT=0.0; $n=0; $status='UNKNOWN'; $msg=''
  while($simT -lt $StopS -and $sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
    $n++
    try { $c.RunSimulation($ChunkS, $true) } catch { $msg=$_.Exception.Message }
    $w=[Diagnostics.Stopwatch]::StartNew()
    while($w.Elapsed.TotalSeconds -lt 120){ Start-Sleep -Milliseconds 100; $st=$c.SimulationState; if($st -eq 2 -or $st -eq 0){break} }
    $er=$c.LastErrorMessage
    Write-Output ('  chunk ' + $n + ' t<=' + $simT.ToString('E6') + ' state=' + $c.SimulationState + ' err=' + $er)
    if($er -and $er.Length -gt 0){ $status='ERROR'; $msg=$er; break }
    if($c.SimulationState -eq 0){ $status='STOPPED'; break }
    $simT += $ChunkS
  }
  if(@('ERROR','STOPPED') -notcontains $status){ $status='REACHED' }
  Write-Output ('RESULT ' + $Tag + ' status=' + $status + ' lastGoodT=' + $simT.ToString('E6') + ' msg=' + $msg)
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'