# ASCII-only. Verify Multisim accepts the re-encoded .ms14 and honours the patched settings.
# env: MS_EXE, MS_DEBUGDIR, MS_IN, MS_RESAVED
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'verify_fixed.txt'
function W([string]$m) { Write-Output $m; Add-Content -LiteralPath $logf -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $logf -Value ("verify " + (Get-Date)) -Encoding UTF8

if (Test-Path $env:MS_RESAVED) { Remove-Item $env:MS_RESAVED -Force }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.Connect()
W ("connected=" + $a.IsConnected + " ver=" + $a.VersionInfo)
try {
    $c = $a.OpenFile($env:MS_IN)
    if ($null -eq $c) { W "OpenFile returned NULL"; } else {
        W ("opened CircuitName='" + $c.CircuitName + "' FileName='" + $c.FileName + "'")
        $comps = @($c.EnumComponents(0))
        W ("components count=" + $comps.Count + " -> " + ($comps -join ','))
        W ("variants = " + (@($c.EnumVariants()) -join ','))
        W ("RLCValue(RLOAD) = " + $c.RLCValue('RLOAD'))
        W ("RLCValue(CBB)   = " + $c.RLCValue('CBB'))
        W ("RLCValue(RRF)   = " + $c.RLCValue('RRF'))
        $r = $c.SaveAs($env:MS_RESAVED)
        W ("SaveAs -> '" + $r + "'")
    }
} catch { W ("EXC " + $_.Exception.Message + " lastErr='" + $a.LastErrorMessage + "'") }
W ("app LastErrorMessage='" + $a.LastErrorMessage + "'")
try { $a.Disconnect() } catch {}
W ("resaved exists: " + (Test-Path $env:MS_RESAVED) + " size=" + (Get-Item $env:MS_RESAVED -ErrorAction SilentlyContinue).Length)
W "verify done"
