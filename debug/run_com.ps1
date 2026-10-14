# ASCII-only. Runs the interactive simulation in bounded chunks and logs state + errors.
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$tag    = $env:MS_TAG
$logf   = Join-Path $outdir ("run_" + $tag + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("run start " + (Get-Date) + " tag=" + $tag) -Encoding UTF8

$chunk = [double]$env:MS_CHUNK
$maxN  = [int]$env:MS_MAXCHUNK
$pause = ($env:MS_PAUSE -eq '1')

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir ("multisim_api_" + $tag + ".log"))
$a.Connect()
W ("connected=" + $a.IsConnected + " ver=" + $a.VersionInfo)
$c = $a.OpenFile($env:MS_DEBUG)
W ("opened '" + $c.CircuitName + "'")
W ("state=" + $c.SimulationState)

# ask for the nodes of interest
foreach ($n in @('V(TP3)', 'V(TP2)', 'V(V1)', 'V(TP6)', 'V(V2)', 'V(TP5)')) {
    try { $c.SetOutputRequest($n, 0, 0, 0, $false); W ("SetOutputRequest " + $n + " ok") }
    catch { W ("SetOutputRequest " + $n + " ERR " + $_.Exception.Message) }
}

$t0 = Get-Date
for ($i = 1; $i -le $maxN; $i++) {
    $ts = Get-Date
    try {
        $c.RunSimulation($chunk, $pause)
        $st = $c.SimulationState
        $er = $c.LastErrorMessage
        $simt = [math]::Round($i * $chunk * 1e6, 3)
        W ("chunk " + $i + " simt<=" + $simt + "us wall=" + [math]::Round(((Get-Date) - $ts).TotalSeconds, 2) + "s state=" + $st + " err='" + $er + "'")
        if ($er -and $er.Length -gt 0) { W ("*** SIMULATOR MESSAGE: " + $er); break }
        if ($st -eq 0 -and $i -gt 1) { W ("*** state=Stopped at chunk " + $i); break }
    } catch {
        W ("chunk " + $i + " EXC " + $_.Exception.Message)
        W ("     LastErrorMessage='" + $c.LastErrorMessage + "'")
        break
    }
    if (((Get-Date) - $t0).TotalSeconds -gt 900) { W "*** wall clock budget exceeded, stopping"; break }
}

W ("final state=" + $c.SimulationState + " err='" + $c.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W "run done"
