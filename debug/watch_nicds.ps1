# ASCII-only. Poll a directory and copy any new/changed file to a capture dir.
# env: MS_NICDS, MS_CAPTURE, MS_SECS
$ErrorActionPreference = 'Continue'
$src = $env:MS_NICDS
$dst = $env:MS_CAPTURE
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$known = @{}
$deadline = (Get-Date).AddSeconds([int]$env:MS_SECS)
$n = 0
while ((Get-Date) -lt $deadline) {
    if (Test-Path $src) {
        foreach ($f in (Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue)) {
            $key = $f.FullName
            $prev = $null; if ($known.ContainsKey($key)) { $prev = $known[$key] }
            if ($prev -ne $f.Length) {
                $known[$key] = $f.Length
                if ($f.Length -gt 0) {
                    $n++
                    $out = Join-Path $dst ("{0:d3}_{1}_{2}" -f $n, $f.Length, $f.Name)
                    try { Copy-Item $f.FullName $out -Force -ErrorAction Stop; Write-Output ("CAPTURED $($f.Name) len=$($f.Length) -> $(Split-Path $out -Leaf)") } catch {}
                } else { Write-Output ("saw empty $($f.Name)") }
            }
        }
    }
    Start-Sleep -Milliseconds 120
}
Write-Output "watch done, captured $n"
