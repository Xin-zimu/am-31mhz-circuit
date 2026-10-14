param([string]$Dir,[string]$OutDir,[string]$ChunkS='0.0000001',[string]$StopS='0.00002',[int]$TimeoutSeconds=600)
$ErrorActionPreference='Continue'
$cs = [double]::Parse($ChunkS, [Globalization.CultureInfo]::InvariantCulture)
$ss = [double]::Parse($StopS, [Globalization.CultureInfo]::InvariantCulture)
if(-not (Test-Path $OutDir)){ New-Item -ItemType Directory -Path $OutDir | Out-Null }
$tags = @('orig_GEAR500_UIC_2ns','proj_TMAX1ns','V_2n_1n','V_1n_2n','V_2n_2n','V_1n_1n')
foreach($tag in $tags){
  $proj = Join-Path $Dir ($tag + '.ms14')
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $log = Join-Path $OutDir ($tag + '.api.log')
  if(Test-Path $log){ Remove-Item $log -Force }
  $a = New-Object -ComObject MultisimInterface.MultisimApp
  $a.Path = 'D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $a.LogFile = $log
  $a.Connect()
  $status='UNKNOWN'; [double]$simT=0.0; [int]$chunks=0; $msg=''
  try {
    $c = $a.OpenFile($proj)
    while($simT -lt $ss){
      $chunks = $chunks + 1
      try { $c.RunSimulation($cs, $true) } catch { $msg = $_.Exception.Message }
      $w=[Diagnostics.Stopwatch]::StartNew()
      while($w.Elapsed.TotalSeconds -lt 60){ Start-Sleep -Milliseconds 100; $st=$c.SimulationState; if($st -eq 2 -or $st -eq 0){ break } }
      $er = $c.LastErrorMessage
      if($er -and $er.Length -gt 0){ $status='ERROR'; $msg=$er; break }
      $simT = $simT + $cs
      if($c.SimulationState -eq 0){ $status='SOLVER-STOPPED'; break }
    }
    if($status -eq 'UNKNOWN'){ $status='REACHED-TSTOP' }
  } catch { $status='EXC'; $msg=$_.Exception.Message }
  finally { try{$a.Disconnect()}catch{} }
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Write-Output ('=== ' + $tag + ' status=' + $status + ' reached=' + $simT.ToString('E6') + ' chunks=' + $chunks)
  if(Test-Path $log){ Get-Content $log | Select-String -Pattern 'tmax|Error|error|converge|Converge' | Select-Object -First 4 | ForEach-Object { Write-Output ('    ' + $_.Line) } }
  Start-Sleep -Seconds 2
}
Write-Output 'DONE'