$ErrorActionPreference='Continue'
$B='D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹'
$res=@()
foreach($v in @('V_tstep2n_tmax2n','V_tstep2n_tmax1n','V_tstep1n_tmax2n','V_tstep1n_tmax1n','V_tstep2n_tmax1_5n','V_tstep2n_tmax1_05n')){
  Get-Process -Name multisim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $proj = Join-Path $B ('工作副本\' + $v + '.ms14')
  $out = & powershell -NoProfile -Command "& '$B\run_project_analysis.ps1' -Project '$proj' -Tag $v -ChunkS 1e-7 -StopS 2e-5 -TimeoutSeconds 400"
  $line = ($out | Where-Object { $_ -match 'RESULT|REACHED|FAILED|solver stopped' }) -join ' | '
  Write-Output ($v + ' => ' + $line)
  $res += ($v + ' => ' + $line)
}
$res | Set-Content -LiteralPath ($B + '\variant_results.txt') -Encoding UTF8
Write-Output 'ALL DONE'