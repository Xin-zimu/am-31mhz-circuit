# ASCII-only. Tests: open a .cir netlist copy, enumerate, SaveAs .ms14.
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'probe2.out.txt'
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("probe2 start " + (Get-Date)) -Encoding UTF8

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir 'multisim_api.log')
$a.Connect()
W ("connected=" + $a.IsConnected + " ver=" + $a.VersionInfo)

try {
    $c = $a.OpenFile($env:MS_CIR)
    if ($null -eq $c) { W "OpenFile(.cir) returned NULL" }
    else {
        W ("opened .cir ok: CircuitName='" + $c.CircuitName + "' FileName='" + $c.FileName + "'")
        W ("components = " + (@($c.EnumComponents(0)) -join ', '))
        W ("variants   = " + (@($c.EnumVariants()) -join ', '))
        try { $r = $c.SaveAs($env:MS_SAVEAS); W ("SaveAs -> '" + $r + "'") }
        catch { W ("SaveAs ERR " + $_.Exception.Message) }
    }
} catch { W ("FATAL cir open: " + $_.Exception.Message) }
W ("app LastErrorMessage='" + $a.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W "probe2 done"
