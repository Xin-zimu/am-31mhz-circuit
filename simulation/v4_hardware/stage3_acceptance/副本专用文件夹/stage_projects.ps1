$ErrorActionPreference='Stop'
$src = 'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance'
$srcWork = Join-Path $src '副本专用文件夹\工作副本'
$dst = 'D:\ms_xsp\stage3_acceptance\proj'
if(-not (Test-Path $dst)){ New-Item -ItemType Directory -Path $dst | Out-Null }
Get-ChildItem $dst -File | Remove-Item -Force
$map = @()
$list = @(
  @{tag='orig_GEAR500_UIC_2ns';  path=(Join-Path $src 'S03_COLD_ZERO_GEAR500_UIC_20us.ms14')},
  @{tag='proj_TMAX1ns';          path=(Join-Path $src 'S03_COLD_ZERO_GEAR500_UIC_TMAX1ns_20us.ms14')},
  @{tag='V_2n_2n';              path=(Join-Path $srcWork 'V_tstep2n_tmax2n.ms14')},
  @{tag='V_1n_1n';              path=(Join-Path $srcWork 'V_tstep1n_tmax1n.ms14')},
  @{tag='V_2n_1n';              path=(Join-Path $srcWork 'V_tstep2n_tmax1n.ms14')},
  @{tag='V_1n_2n';              path=(Join-Path $srcWork 'V_tstep1n_tmax2n.ms14')},
  @{tag='V_2n_1500p';           path=(Join-Path $srcWork 'V_tstep2n_tmax1_5n.ms14')},
  @{tag='V_2n_1050p';           path=(Join-Path $srcWork 'V_tstep2n_tmax1_05n.ms14')}
)
foreach($e in $list){
  if(-not (Test-Path $e.path)){ Write-Output ('MISSING ' + $e.tag); continue }
  $d = Join-Path $dst ($e.tag + '.ms14')
  Copy-Item -LiteralPath $e.path -Destination $d -Force
  $h = (Get-FileHash -Algorithm SHA256 $d).Hash.Substring(0,16)
  Write-Output ('{0}  {1}  {2}' -f $e.tag, $h, (Get-Item $d).Length)
}
Write-Output ('staged: ' + (Get-ChildItem $dst -File).Count + ' in ' + $dst)
