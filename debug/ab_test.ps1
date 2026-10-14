# ASCII-only. Controlled experiment: produce two .ms14 files differing by ONE component value.
# env: MS_DEBUG, MS_EXE, MS_DEBUGDIR, MS_A, MS_B, MS_COMP, MS_VAL
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'ab_test.txt'
function W([string]$m) { Write-Output $m; Add-Content -LiteralPath $logf -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $logf -Value ("ab test " + (Get-Date)) -Encoding UTF8

foreach ($p in @($env:MS_A, $env:MS_B)) { if (Test-Path $p) { Remove-Item $p -Force } }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.Connect()
$c = $a.OpenFile($env:MS_DEBUG)
W ("opened '" + $c.CircuitName + "'")
W ("RLCValue(" + $env:MS_COMP + ") = " + $c.RLCValue($env:MS_COMP))
W ("SaveAs A -> " + $c.SaveAs($env:MS_A))

try {
    $c.RLCValue($env:MS_COMP) = [double]$env:MS_VAL
    W ("set RLCValue ok; now = " + $c.RLCValue($env:MS_COMP))
} catch { W ("set RLCValue EXC " + $_.Exception.Message) }
W ("SaveAs B -> " + $c.SaveAs($env:MS_B))

foreach ($p in @($env:MS_A, $env:MS_B)) {
    if (Test-Path $p) { W ("file " + (Split-Path $p -Leaf) + " size=" + (Get-Item $p).Length) } else { W ("MISSING " + $p) }
}
try { $a.Disconnect() } catch {}
W "ab test done"
