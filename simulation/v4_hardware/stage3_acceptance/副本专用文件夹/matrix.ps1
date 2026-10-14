# Serial TMAX/TSTEP matrix. ASCII-only. One Multisim instance at a time.
param([string]$Dir,[string]$Out,[double]$ChunkS=1e-7,[double]$StopS=2e-5,[int]$TimeoutSeconds=600)
$ErrorActionPreference='Continue'
$tags = @('orig_GEAR500_UIC_2ns','proj_TMAX1ns','V_2n_2n','V_1n_1n','V_2n_1n','V_1n_2n','V_2n_1500p','V_2n_1050p')
$rows = @()
foreach($tag in $tags){
  $proj = Join-Path $Dir ($tag + '.ms14')
  if(-not (Test-Path $proj)){ $rows += [pscustomobject]@{tag=$tag;status='MISSING';reached_s=$null;chunks=0;wall_s=0;msg=''}; continue }
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $a = New-Object -ComObject MultisimInterface.MultisimApp
  $a.Path = 'D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $a.Connect()
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $status='UNKNOWN'; $simT=0.0; $msg=''; $chunks=0
  try {
    $c = $a.OpenFile($proj)
    while($simT -lt $StopS -and $sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
      $chunks++
      try { $c.RunSimulation($ChunkS, $true) } catch { $msg = $_.Exception.Message }
      $w=[Diagnostics.Stopwatch]::StartNew()
      while($w.Elapsed.TotalSeconds -lt 120){ Start-Sleep -Milliseconds 100; $st=$c.SimulationState; if($st -eq 2 -or $st -eq 0){ break } }
      $er = $c.LastErrorMessage
      if($er -and $er.Length -gt 0){ $status='ERROR'; $msg=$er; break }
      $simT += $ChunkS
      if($c.SimulationState -eq 0){ $status='SOLVER-STOPPED'; break }
    }
    if($status -eq 'UNKNOWN'){ $status='REACHED-TSTOP' }
  } catch { $status='EXC'; $msg=$_.Exception.Message }
  finally { try{$a.Disconnect()}catch{} }
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $row = [pscustomobject]@{tag=$tag;status=$status;reached_s=$simT;chunks=$chunks;wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1);msg=$msg}
  $rows += $row
  Write-Output ($tag + ' status=' + $status + ' reached=' + $simT.ToString('E3') + ' chunks=' + $chunks + ' wall=' + $row.wall_s + 's msg=' + $msg)
  Start-Sleep -Seconds 2
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Out -Encoding UTF8
Write-Output 'MATRIX DONE'