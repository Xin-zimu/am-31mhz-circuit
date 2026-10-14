$ErrorActionPreference='Stop'
$base = 'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance'
$keep = Join-Path $base '副本专用文件夹'
$orig = Join-Path $keep '原始只读引用'
$work = Join-Path $keep '工作副本'
foreach($d in @($orig,$work)){ if(-not (Test-Path $d)){ New-Item -ItemType Directory -Path $d | Out-Null } }

# Byte-for-byte references of the authoritative sources (never edited)
$srcs = @(
 'S03_BASELINE_V4_3.ms14',
 'S03_GUI_2ms_V4_3.ms14',
 'S03_COLD_ZERO_2ms_V4_3.ms14',
 'S03_COLD_ZERO_TRAP100_FAILURE.ms14',
 'S03_COLD_ZERO_TRAP500_20us.ms14',
 'S03_COLD_ZERO_GEAR500_20us.ms14',
 'S03_COLD_ZERO_GEAR500_UIC_20us.ms14',
 'S03_COLD_ZERO_GEAR500_UIC_TMAX1ns_20us.ms14',
 'cold_gui_actual.cir',
 'cold_engine_gui_net.cir',
 'nominal_full.cir'
)
$rows = @()
foreach($s in $srcs){
  $p = Join-Path $base $s
  if(-not (Test-Path $p)){ $rows += [pscustomobject]@{file=$s; status='MISSING'}; continue }
  $d = Join-Path $orig $s
  Copy-Item -LiteralPath $p -Destination $d -Force
  $h1 = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
  $h2 = (Get-FileHash -LiteralPath $d -Algorithm SHA256).Hash
  $rows += [pscustomobject]@{file=$s; status=if($h1 -eq $h2){'OK'}else{'HASH-MISMATCH'}; bytes=(Get-Item $p).Length; sha256=$h1.Substring(0,16); tmax=(Get-Date (Get-Item $p).LastWriteTime -Format 'MM-dd HH:mm')}
}
$rows | Format-Table -AutoSize | Out-String -Width 200
'--- 原始只读引用 count: ' + (Get-ChildItem $orig -File).Count
