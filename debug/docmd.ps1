# ASCII-only. Drives Multisim's XSPICE engine via IMultisimCircuit.DoCommandLine.
# env: MS_DEBUGDIR, MS_EXE, MS_CMDFILE, MS_XSPLOG, MS_TAG, MS_WAITSEC
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$tag    = $env:MS_TAG
$logf   = Join-Path $outdir ("docmd_" + $tag + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("docmd start " + (Get-Date) + " tag=" + $tag) -Encoding UTF8

$xlog = $env:MS_XSPLOG
if (Test-Path $xlog) { Remove-Item $xlog -Force }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir ("multisim_api_" + $tag + ".log"))
$a.Connect()
W ("connected=" + $a.IsConnected)

$c = $a.NewFile()
W ("NewFile -> '" + $c.CircuitName + "'")

$t0 = Get-Date
try {
    $c.DoCommandLine($env:MS_CMDFILE, $xlog)
    W ("DoCommandLine returned ok")
} catch { W ("DoCommandLine EXC " + $_.Exception.Message) }

# poll the XSPICE log until it stops growing
$maxWait = [int]$env:MS_WAITSEC
$last = -1; $stable = 0
while (((Get-Date) - $t0).TotalSeconds -lt $maxWait) {
    Start-Sleep -Milliseconds 700
    $sz = 0
    if (Test-Path $xlog) { $sz = (Get-Item $xlog).Length }
    if ($sz -eq $last) { $stable++ } else { $stable = 0; $last = $sz }
    if ($stable -ge 6 -and $sz -gt 0) { break }
}
W ("waited " + [math]::Round(((Get-Date) - $t0).TotalSeconds, 1) + "s, log size=" + $last)
W ("SimulationState=" + $c.SimulationState + " LastErrorMessage='" + $c.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W "docmd done"
