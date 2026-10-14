param([string]$Dir,[string]$Out,[string]$ChunkS='0.0000001',[string]$StopS='0.00002',[int]$TimeoutSeconds=600)
$ErrorActionPreference='Continue'
$cs = [double]::Parse($ChunkS, [Globalization.CultureInfo]::InvariantCulture)
$ss = [double]::Parse($StopS, [Globalization.CultureInfo]::InvariantCulture)
Write-Output ('chunk=' + $cs.ToString('R') + ' stop=' + $ss.ToString('R'))
$tags = @('orig_GEAR500_UIC_2ns','proj_TMAX1ns','V_2n_2n','V_1n_1n','V_2n_1n','V_1n_2n','V_2n_1500p','V_2n_1050p')
$rows = @()
foreach($tag in $tags){
  $proj = Join-Path $Dir ($tag + '.ms14')
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $a = New-Object -ComObject MultisimInterface.MultisimApp
  $a.Path = 'D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $a.Connect()
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $status='UNKNOWN'; [double]$simT=0.0; $msg=''; [int]$chunks=0
  try {
    $c = $a.OpenFile($proj)
    while($simT -lt $ss -and $sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
      $chunks = $chunks + 1
      try { $c.RunSimulation($cs, $true) } catch { $msg = $_.Exception.Message }
      $w=[Diagnostics.Stopwatch]::StartNew()
      while($w.Elapsed.TotalSeconds -lt 120){ Start-Sleep -Milliseconds 100; $st=$c.SimulationState; if($st -eq 2 -or $st -eq 0){ break } }
      $er = $c.LastErrorMessage
      if($er -and $er.Length -gt 0){ $status='ERROR'; $msg=$er; break }
      $simT = $simT + $cs
      if($c.SimulationState -eq 0){ $status='SOLVER-STOPPED'; break }
    }
    if($status -eq 'UNKNOWN'){ $status='REACHED-TSTOP' }
  } catch { $status='EXC'; $msg=$_.Exception.Message }
  finally { try{$a.Disconnect()}catch{} }
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $row = [pscustomobject]@{tag=$tag;status=$status;reached_s=$simT;chunks=$chunks;wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1);msg=$msg}
  $rows += $row
  Write-Output ($tag + ' status=' + $status + ' reached=' + $simT.ToString('E6') + ' chunks=' + $chunks + ' wall=' + $row.wall_s + 's msg=' + $msg)
  Start-Sleep -Seconds 2
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Out -Encoding UTF8
Write-Output 'MATRIX DONE'