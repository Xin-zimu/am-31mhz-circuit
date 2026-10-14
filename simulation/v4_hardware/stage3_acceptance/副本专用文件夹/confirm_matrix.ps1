param([string]$Dir,[string]$OutDir,[string]$ChunkS='0.0000001',[string]$StopS='0.000005',[int]$Runs=2)
$ErrorActionPreference='Continue'
$cs=[double]::Parse($ChunkS,[Globalization.CultureInfo]::InvariantCulture)
$ss=[double]::Parse($StopS,[Globalization.CultureInfo]::InvariantCulture)
$tags=@('V_1n_1n','V_2n_1n','V_1n_2n','V_2n_2n')
foreach($rep in 1..$Runs){
 foreach($tag in $tags){
  $proj=Join-Path $Dir ($tag+'.ms14')
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $a=New-Object -ComObject MultisimInterface.MultisimApp
  $a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $a.Connect()
  $status='UNKNOWN'; [double]$simT=0.0; [int]$ch=0; $msg=''
  try{
   $c=$a.OpenFile($proj)
   while($simT -lt $ss){
    $ch=$ch+1
    try{$c.RunSimulation($cs,$true)}catch{$msg=$_.Exception.Message}
    $w=[Diagnostics.Stopwatch]::StartNew()
    while($w.Elapsed.TotalSeconds -lt 60){Start-Sleep -Milliseconds 100;$st=$c.SimulationState;if($st -eq 2 -or $st -eq 0){break}}
    $er=$c.LastErrorMessage
    if($er){$status='ERROR';$msg=$er;break}
    $simT=$simT+$cs
    if($c.SimulationState -eq 0){$status='SOLVER-STOPPED';break}
   }
   if($status -eq 'UNKNOWN'){$status='REACHED' }
  }catch{$status='EXC';$msg=$_.Exception.Message}finally{try{$a.Disconnect()}catch{}}
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Write-Output ('run' + $rep + ' ' + $tag + ' status=' + $status + ' reached=' + $simT.ToString('E6') + ' chunks=' + $ch)
  Start-Sleep -Seconds 2
 }
}
Write-Output 'CONFIRM DONE'