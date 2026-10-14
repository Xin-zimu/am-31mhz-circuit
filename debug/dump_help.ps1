# ASCII-only helper: dump Multisim help HTML pages as plain text.
param([string[]]$Names, [int]$Max = 4000)
$h = $env:MS_HELPDIR
foreach ($n in $Names) {
    $p = Join-Path $h ($n + '.html')
    Write-Output ("================ " + $n)
    if (-not (Test-Path $p)) { Write-Output "  (missing)"; continue }
    $t = Get-Content $p -Raw -Encoding UTF8
    $t = $t -replace '(?s)<script.*?</script>', ' ' -replace '(?s)<style.*?</style>', ' '
    $t = $t -replace '(?s)<!--.*?-->', ' '
    $t = $t -replace '<br\s*/?>', "`n" -replace '</p>', "`n" -replace '</div>', "`n" -replace '</tr>', "`n" -replace '</li>', "`n"
    $t = $t -replace '<[^>]+>', ''
    $t = [System.Web.HttpUtility]::HtmlDecode($t)
    $t = ($t -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }) -join "`n"
    $t = $t -replace '\n{3,}', "`n`n"
    if ($t.Length -gt $Max) { $t = $t.Substring(0, $Max) + "`n...[truncated]" }
    Write-Output $t
}
