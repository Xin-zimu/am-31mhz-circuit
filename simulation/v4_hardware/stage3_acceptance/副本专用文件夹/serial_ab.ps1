# Serial A/B: one Multisim instance at a time to remove cross-instance interference.
param([string]$Stage,[string]$OutDir,[double]$ChunkS=2e-8,[double]$StopS=2e-5,[int]$TimeoutSeconds=1800)
$ErrorActionPreference='Continue'
if(-not (Test-Path $OutDir)){ New-Item -ItemType Directory -Path $OutDir | Out-Null }
$CASES = @(
  @{Tag='TMAX1ns';      File='S03_COLD_ZERO_GEAR500_UIC_TMAX1ns_20us.ms14'},
  @{Tag='GEAR500_UIC_2n';File='S03_COLD_ZERO_GEAR500_UIC_20us.ms14'},
  @{Tag='GEAR500_2n';    File='S03_COLD_ZERO_GEAR500_20us.ms14'},
  @{Tag='TRAP500_2n';    File='S03_COLD_ZERO_TRAP500_20us.ms14'}
)
$summary = @()
foreach($case in $CASES){
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $log = Join-Path $OutDir ($case.Tag + '.run.txt')
  $a = New-Object -ComObject MultisimInterface.MultisimApp
  $a.Path = 'D:\multimism\Circuit Design Suite 14.3\multisim.exe'
  $a.Connect()
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $status = 'unknown'; $simT = 0.0; $msg = ''; $chunks = 0
  try {
    $c = $a.OpenFile((Join-Path $Stage $case.File))
    while($simT -lt $StopS -and $sw.Elapsed.TotalSeconds -lt $TimeoutSeconds){
      $chunks++
      try { $c.RunSimulation($ChunkS, $true) } catch { $msg = $_.Exception.Message }
      $w=[Diagnostics.Stopwatch]::StartNew()
      while($w.Elapsed.TotalSeconds -lt 180){
        Start-Sleep -Milliseconds 150
        $st=$c.SimulationState
        if($st -eq 2 -or $st -eq 0){ break }
      }
      $er = $c.LastErrorMessage
      if($er -and $er.Length -gt 0){ $status='ERROR'; $msg=$er; break }
      $simT += $ChunkS
      if($c.SimulationState -eq 0){ $status='SOLVER-STOPPED'; break }
    }
    if($status -eq 'unknown'){ $status='REACHED-STOP' }
  } catch { $status='EXC'; $msg=$_.Exception.Message }
  finally { try{$a.Disconnect()}catch{} }
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $line = ('{0,-16} status={1,-16} reached~{2:E3}s chunks={3} wall={4}s msg={5}' -f $case.Tag,$status,$simT,$chunks,[math]::Round($sw.Elapsed.TotalSeconds,1),$msg)
  Write-Output $line
  Add-Content -LiteralPath $log -Value $line -Encoding UTF8
  $summary += [pscustomobject]@{tag=$case.Tag; file=$case.File; status=$status; reached_s=$simT; chunks=$chunks; wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1); msg=$msg}
  Start-Sleep -Seconds 2
}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutDir 'serial_ab_summary.json') -Encoding UTF8
Write-Output '--- serial A/B complete ---'