# ASCII-only. Open each patched project in Multisim and Save() it natively, reporting state.
# env: MS_EXE, MS_DEBUGDIR, MS_FILES (semicolon-separated paths)
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'finalize.txt'
function W([string]$m) { Write-Output $m; Add-Content -LiteralPath $logf -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $logf -Value ("finalize " + (Get-Date)) -Encoding UTF8

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.Connect()
W ("connected=" + $a.IsConnected)

foreach ($f in ($env:MS_FILES -split ';')) {
    if (-not (Test-Path $f)) { W ("MISSING " + $f); continue }
    W ("=============== " + $f)
    W ("  size before = " + (Get-Item $f).Length)
    try {
        $c = $a.OpenFile($f)
        $comps = @($c.EnumComponents(0))
        W ("  opened '" + $c.CircuitName + "' components=" + $comps.Count)
        W ("  variants = " + (@($c.EnumVariants()) -join ','))
        W ("  RLOAD=" + $c.RLCValue('RLOAD') + " CBB=" + $c.RLCValue('CBB') + " RRF=" + $c.RLCValue('RRF'))
        $r = $c.Save()
        W ("  Save() -> " + $r)
    } catch { W ("  EXC " + $_.Exception.Message + " lastErr='" + $a.LastErrorMessage + "'") }
    W ("  size after  = " + (Get-Item $f).Length)
}
W ("app LastErrorMessage='" + $a.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W "finalize done"
