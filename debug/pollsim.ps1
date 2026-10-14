# ASCII-only. Starts the circuit's own Transient Analysis via COM (asynchronous) and polls it.
# env: MS_DEBUGDIR, MS_DEBUG, MS_EXE, MS_TAG, MS_RUNSEC, MS_POLLSEC, MS_NICDS
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$tag    = $env:MS_TAG
$logf   = Join-Path $outdir ("poll_" + $tag + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("poll " + (Get-Date)) -Encoding UTF8

$nicds = $env:MS_NICDS
$before = @{}
if (Test-Path $nicds) { Get-ChildItem $nicds -File | ForEach-Object { $before[$_.FullName] = $_.Length } }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir ("multisim_api_" + $tag + ".log"))
$a.Connect()
$c = $a.OpenFile($env:MS_DEBUG)
W ("opened '" + $c.CircuitName + "' state=" + $c.SimulationState)

$runsec = [double]$env:MS_RUNSEC
$t0 = Get-Date
try { $c.RunSimulation($runsec, $true); W ("RunSimulation(" + $runsec + ", pause) accepted") }
catch { W ("RunSimulation EXC " + $_.Exception.Message + " lastErr='" + $c.LastErrorMessage + "'") }

$deadline = (Get-Date).AddSeconds([int]$env:MS_POLLSEC)
$lastState = -99
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
    $st = -1; $er = ''
    try { $st = $c.SimulationState } catch { $st = -2 }
    try { $er = $c.LastErrorMessage } catch {}
    $p = Get-Process -Name multisim -ErrorAction SilentlyContinue
    if (-not $p) { W "*** multisim process GONE (crash)"; break }
    $ws = [math]::Round($p[0].WorkingSet64/1MB,1)
    if ($st -ne $lastState -or $er) { W ("t+" + [math]::Round(((Get-Date)-$t0).TotalSeconds,1) + "s state=" + $st + " ws=" + $ws + "MB err='" + $er + "'"); $lastState = $st }
    if ($er -and $er.Length -gt 0) { W ("*** ANALYSIS MESSAGE: " + $er); break }
    if (Test-Path $nicds) {
        foreach ($f in (Get-ChildItem $nicds -File)) {
            $prev = -1; if ($before.ContainsKey($f.FullName)) { $prev = $before[$f.FullName] }
            if ($f.Length -ne $prev) { W ("   NICDS {0}: {1} -> {2}" -f $f.Name, $prev, $f.Length); $before[$f.FullName] = $f.Length }
        }
    }
}
try { $c.StopSimulation(); W "StopSimulation issued" } catch { W ("StopSimulation ERR " + $_.Exception.Message) }
W ("final state=" + $c.SimulationState + " err='" + $c.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W "poll done"
