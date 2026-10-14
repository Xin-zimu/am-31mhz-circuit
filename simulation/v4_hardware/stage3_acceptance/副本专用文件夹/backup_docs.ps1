$ErrorActionPreference='Stop'
$stage='D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance'
$proj='D:\实验报告文件夹\电路2\项目管理'
$bk=Join-Path $stage '副本专用文件夹\原始只读引用'
foreach($f in @('S03_04_冷启动排查记录.md','S03_GUI复跑报告.md')){
  $src=Join-Path $stage $f
  if(Test-Path $src){ Copy-Item -LiteralPath $src -Destination (Join-Path $bk ($f -replace '\.md$','_原始.md')) -Force; Write-Output ('backed up: '+$f) }
}
foreach($f in @('03_当前实现状态.md','02_当前阶段目标.md')){
  $src=Join-Path $proj $f
  if(Test-Path $src){ Copy-Item -LiteralPath $src -Destination (Join-Path $bk ($f -replace '\.md$','_原始.md')) -Force; Write-Output ('backed up: '+$f) }
}
Get-ChildItem $bk -File | Select-Object Name,Length | Format-Table -AutoSize | Out-String -Width 200
