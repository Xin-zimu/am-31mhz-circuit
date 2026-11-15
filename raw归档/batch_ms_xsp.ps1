# ms_xsp B/C 档批量处理驱动器：逐批 归档→核验→删除，留进度日志
$ErrorActionPreference = 'Continue'
$py = 'C:\Users\86139\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$tool = 'D:\实验报告文件夹\电路2\raw归档\raw_archive.py'
$ver = 'D:\实验报告文件夹\电路2\raw归档\verify_and_delete.py'
$outRoot = 'D:\实验报告文件夹\电路2\raw归档'
$logFile = "$outRoot\batch_log.txt"

$batches = @(
  's05_parts_20261030',
  's05_measurement_20261030',
  'v3_20k',
  'v4_lm393',
  's04_poly_20261016',
  's04_power_20261016',
  's04_3904_20261029',
  's04_c518062_20261016',
  's04_crosscheck_20261017',
  'repair_20261011',
  's05_parts_tran_20261030',
  's05_gain_20261030',
  's05_blocker_20261029',
  's05_receiver_20261029',
  's05_selectivity_20261029'
)

"$(Get-Date -Format 'HH:mm:ss') 批量处理开始，共 $($batches.Count) 批" | Tee-Object -FilePath $logFile
$allBefore = 0.0
foreach ($b in $batches) {
  $dir = "D:\ms_xsp\$b"
  if (-not (Test-Path $dir)) { "跳过（目录不存在）: $b" | Tee-Object -FilePath $logFile -Append; continue }
  $raws = Get-ChildItem $dir -Filter *.raw
  if ($raws.Count -eq 0) { "跳过（无raw）: $b" | Tee-Object -FilePath $logFile -Append; continue }
  $sizeMB = ($raws | Measure-Object Length -Sum).Sum / 1MB
  $allBefore += $sizeMB
  $arch = "$outRoot\$($b)_归档"
  $t1 = Get-Date
  $msg = "$(Get-Date -Format 'HH:mm:ss') [$b] $($raws.Count) 个 / $([math]::Round($sizeMB,1)) MB → 归档"
  $msg | Tee-Object -FilePath $logFile -Append
  & $py $tool raw_summary $dir $arch 2>&1 | Out-String | Tee-Object -FilePath $logFile -Append
  $ok1 = ($LASTEXITCODE -eq 0)
  if (-not $ok1) { "  [失败] raw_summary exit=$LASTEXITCODE，跳过删除" | Tee-Object -FilePath $logFile -Append; continue }
  & $py $ver "$arch\归档记录.md" $dir --delete 2>&1 | Out-String | Tee-Object -FilePath $logFile -Append
  $ok2 = ($LASTEXITCODE -eq 0)
  $t2 = Get-Date
  $status = if ($ok2) { "完成（已删除）" } else { "删除未执行（核验未通过）" }
  "$(Get-Date -Format 'HH:mm:ss') [$b] $status，耗时 $([math]::Round(($t2-$t1).TotalSeconds,1)) 秒" | Tee-Object -FilePath $logFile -Append
}
$after = (Get-ChildItem 'D:\ms_xsp' -Recurse -File -Filter *.raw | Measure-Object Length -Sum).Sum / 1MB
"$(Get-Date -Format 'HH:mm:ss') 全部完成。本批处理前合计约 $([math]::Round($allBefore,1)) MB；处理后 ms_xsp 剩余 raw 共 $([math]::Round($after,1)) MB" | Tee-Object -FilePath $logFile -Append
