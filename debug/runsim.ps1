# ASCII-only. Drives the circuit's own Transient Analysis through the COM API (no SetOutputRequest).
# env: MS_DEBUGDIR, MS_DEBUG, MS_EXE, MS_TAG, MS_CHUNK, MS_NCHUNK, MS_NICDS
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$tag    = $env:MS_TAG
$logf   = Join-Path $outdir ("runsim_" + $tag + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("runsim " + (Get-Date)) -Encoding UTF8

$nicds = $env:MS_NICDS
$before = @{}
if (Test-Path $nicds) { Get-ChildItem $nicds -File | ForEach-Object { $before[$_.FullName] = $_.Length } }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir ("multisim_api_" + $tag + ".log"))
$a.Connect()
W ("connected=" + $a.IsConnected + " ver=" + $a.VersionInfo)
$c = $a.OpenFile($env:MS_DEBUG)
W ("opened '" + $c.CircuitName + "'")
$outs = @($c.EnumOutputs(0))
W ("EnumOutputs count=" + $outs.Count + " -> " + ($outs -join ','))
W ("state before = " + $c.SimulationState)

$chunk = [double]$env:MS_CHUNK
$n = [int]$env:MS_NCHUNK
for ($i = 1; $i -le $n; $i++) {
    $ts = Get-Date
    try {
        $c.RunSimulation($chunk, $true)
        $st = $c.SimulationState
        $er = $c.LastErrorMessage
        W ("chunk {0} simt<={1}us wall={2}s state={3} err='{4}'" -f $i, [math]::Round($i*$chunk*1e6,1), [math]::Round(((Get-Date)-$ts).TotalSeconds,2), $st, $er)
        if ($er -and $er.Length -gt 0) { W ("*** MESSAGE: " + $er); break }
        if ($st -eq 0 -and $i -gt 1) { W ("*** STOPPED at chunk " + $i); break }
    } catch {
        W ("chunk " + $i + " EXC " + $_.Exception.Message + " lastErr='" + $c.LastErrorMessage + "'")
        break
    }
    if (Test-Path $nicds) {
        foreach ($f in (Get-ChildItem $nicds -File)) {
            $prev = -1; if ($before.ContainsKey($f.FullName)) { $prev = $before[$f.FullName] }
            if ($f.Length -ne $prev) { W ("   NICDS {0}: {1} -> {2}" -f $f.Name, $prev, $f.Length); $before[$f.FullName] = $f.Length }
        }
    }
}
W ("final state=" + $c.SimulationState + " err='" + $c.LastErrorMessage + "'")
$p = Get-Process -Name multisim -ErrorAction SilentlyContinue
if ($p) { W ("multisim ws=" + [math]::Round($p[0].WorkingSet64/1MB,1) + "MB responding=" + $p[0].Responding) } else { W "*** multisim GONE" }
try { $a.Disconnect() } catch {}
W "runsim done"
