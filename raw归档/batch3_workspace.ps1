# workspace 批次：自动枚举 simulation 下所有直接含 *.raw 的目录并处理
$ErrorActionPreference = 'Continue'
$py = 'C:\Users\86139\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$tool = 'D:\实验报告文件夹\电路2\raw归档\raw_archive.py'
$ver = 'D:\实验报告文件夹\电路2\raw归档\verify_and_delete.py'
$outRoot = 'D:\实验报告文件夹\电路2\raw归档'
$logFile = "$outRoot\batch3_workspace_log.txt"
$sim = 'D:\实验报告文件夹\电路2\simulation'

# 枚举所有直接包含 .raw 的目录（含嵌套），排除 D 档关键词目录与活跃阶段（alt1/alt2 另批处理）
$dirs = Get-ChildItem $sim -Directory -Recurse | Where-Object {
  (Get-ChildItem $_.FullName -File -Filter *.raw -ErrorAction SilentlyContinue).Count -gt 0
} | Where-Object { $_.FullName -notmatch 'stage3_acceptance|stage_am_alt' } | Sort-Object FullName

"$(Get-Date -Format 'HH:mm:ss') workspace 批次开始，枚举到 $($dirs.Count) 个含 raw 目录" | Tee-Object -FilePath $logFile
$allBefore = 0.0
foreach ($d in $dirs) {
  $dir = $d.FullName
  $raws = Get-ChildItem $dir -File -Filter *.raw
  if ($raws.Count -eq 0) { continue }
  $sizeMB = ($raws | Measure-Object Length -Sum).Sum / 1MB
  $allBefore += $sizeMB
  $rel = $dir -replace [regex]::Escape($sim + '\'), ''
  $safeName = ($rel -replace '\\', '__')
  $arch = "$outRoot\ws_$($safeName)_归档"
  $t1 = Get-Date
  "$(Get-Date -Format 'HH:mm:ss') [$rel] $($raws.Count) 个 / $([math]::Round($sizeMB,1)) MB → 归档" | Tee-Object -FilePath $logFile -Append
  & $py $tool raw_summary $dir $arch 2>&1 | Out-String | Tee-Object -FilePath $logFile -Append
  $ok1 = ($LASTEXITCODE -eq 0)
  if (-not $ok1) { "  [失败] raw_summary exit=$LASTEXITCODE，跳过删除" | Tee-Object -FilePath $logFile -Append; continue }
  & $py $ver "$arch\归档记录.md" $dir --delete 2>&1 | Out-String | Tee-Object -FilePath $logFile -Append
  $ok2 = ($LASTEXITCODE -eq 0)
  $t2 = Get-Date
  $status = if ($ok2) { "完成（已删除）" } else { "删除未执行（核验未通过）" }
  "$(Get-Date -Format 'HH:mm:ss') [$rel] $status，耗时 $([math]::Round(($t2-$t1).TotalSeconds,1)) 秒" | Tee-Object -FilePath $logFile -Append
}
$after = (Get-ChildItem $sim -Recurse -File -Filter *.raw | Measure-Object Length -Sum).Sum / 1MB
"$(Get-Date -Format 'HH:mm:ss') workspace 批次完成。本批处理前合计约 $([math]::Round($allBefore,1)) MB；处理后 simulation 剩余 raw 共 $([math]::Round($after,1)) MB" | Tee-Object -FilePath $logFile -Append
