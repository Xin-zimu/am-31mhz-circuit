# ASCII-only probe script. Paths come from environment variables (Unicode-safe).
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'probe_com.out.txt'

function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}

Set-Content -LiteralPath $logf -Value ("probe start " + (Get-Date)) -Encoding UTF8
W ("ps bitness: " + [IntPtr]::Size)

try {
    $a = New-Object -ComObject MultisimInterface.MultisimApp
    W ("step1 obj created. Path='" + $a.Path + "' IsConnected=" + $a.IsConnected)
} catch {
    W ("FATAL create: " + $_.Exception.Message)
    exit 1
}

try {
    $a.Path = $env:MS_EXE
    $a.LogFile = (Join-Path $outdir 'multisim_api.log')
    W ("step2 props set: Path='" + $a.Path + "'")
} catch { W ("WARN props: " + $_.Exception.Message) }

try {
    $a.Connect()
    W ("step3 Connect ok. IsConnected=" + $a.IsConnected + " Version='" + $a.VersionInfo + "'")
} catch {
    W ("FATAL connect: " + $_.Exception.Message)
    try { $a.Disconnect() } catch {}
    exit 2
}
W ("app LastErrorMessage = '" + $a.LastErrorMessage + "'")

try {
    $c = $a.OpenFile($env:MS_DEBUG)
    if ($null -eq $c) { W ("FATAL OpenFile returned null") }
    else { W ("step4 OpenFile ok. CircuitName='" + $c.CircuitName + "' FileName='" + $c.FileName + "'") }
} catch { W ("FATAL openfile: " + $_.Exception.Message); $c = $null }

if ($null -ne $c) {
    W ("circuit LastErrorMessage = '" + $c.LastErrorMessage + "'")
    W ("SimulationState = " + $c.SimulationState)

    foreach ($t in @(@('Components',0), @('RLC',1), @('Resistors',2), @('Capacitors',3), @('Inductors',4))) {
        try {
            $v = $c.EnumComponents($t[1])
            W ("EnumComponents(" + $t[0] + ") count=" + @($v).Count + " -> " + (@($v) -join ', '))
        } catch { W ("EnumComponents(" + $t[0] + ") ERR " + $_.Exception.Message) }
    }

    foreach ($t in @(@('All',0), @('Voltage',1), @('Current',2), @('Power',3), @('Digital',4))) {
        try {
            $v = $c.EnumOutputs($t[1])
            W ("EnumOutputs(" + $t[0] + ") count=" + @($v).Count + " -> " + (@($v) -join ', '))
        } catch { W ("EnumOutputs(" + $t[0] + ") ERR " + $_.Exception.Message) }
    }

    try {
        $v = $c.EnumVariants(); W ("EnumVariants -> " + (@($v) -join ', '))
    } catch { W ("EnumVariants ERR " + $_.Exception.Message) }

    try {
        $v = $c.EnumCircuitParameters(0)
        W ("EnumCircuitParameters count=" + @($v).Count)
        foreach ($p in @($v)) {
            try { W ("  param '" + $p + "' = " + $c.CircuitParameterValue($p)) }
            catch { W ("  param '" + $p + "' value ERR " + $_.Exception.Message) }
        }
    } catch { W ("EnumCircuitParameters ERR " + $_.Exception.Message) }

    try {
        $nl = $c.ReportNetlist($false, 0, (Join-Path $outdir 'multisim_netlist.txt'))
        W ("ReportNetlist returned " + ("" + $nl).Length + " chars")
    } catch { W ("ReportNetlist ERR " + $_.Exception.Message) }

    try { $img = $c.GetCircuitImage(0, (Join-Path $outdir 'schematic.png')); W ("GetCircuitImage -> " + $img) }
    catch { W ("GetCircuitImage ERR " + $_.Exception.Message) }
}

W ("final app LastErrorMessage = '" + $a.LastErrorMessage + "'")
try { $a.Disconnect(); W ("disconnected") } catch { W ("disconnect ERR " + $_.Exception.Message) }
W ("probe done")
