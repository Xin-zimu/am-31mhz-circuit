# ASCII-only. Runs the 200us transient through Multisim's XSPICE engine AND pushes the
# waveforms to the Multisim Grapher, then keeps the session alive so the user can look at it.
# env: MS_DEBUGDIR, MS_EXE, MS_CMDFILE, MS_XSPLOG, MS_TAG, MS_WAITSEC, MS_HOLD
$ErrorActionPreference = 'Continue'
Add-Type -Namespace PL -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$outdir = $env:MS_DEBUGDIR
$tag    = $env:MS_TAG
$logf   = Join-Path $outdir ("plot_" + $tag + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("plot run " + (Get-Date)) -Encoding UTF8

$xlog = $env:MS_XSPLOG
if (Test-Path $xlog) { Remove-Item $xlog -Force }

$a = New-Object -ComObject MultisimInterface.MultisimApp
$a.Path = $env:MS_EXE
$a.LogFile = (Join-Path $outdir ("multisim_api_" + $tag + ".log"))
$a.Connect()
W ("connected=" + $a.IsConnected)
$c = $a.NewFile()
W ("NewFile='" + $c.CircuitName + "'")
$t0 = Get-Date
try { $c.DoCommandLine($env:MS_CMDFILE, $xlog); W "DoCommandLine ok" } catch { W ("DoCommandLine EXC " + $_.Exception.Message) }

$maxWait = [int]$env:MS_WAITSEC
$last = -1; $stable = 0
while (((Get-Date) - $t0).TotalSeconds -lt $maxWait) {
    Start-Sleep -Milliseconds 800
    $sz = 0; if (Test-Path $xlog) { $sz = (Get-Item $xlog).Length }
    if ($sz -eq $last) { $stable++ } else { $stable = 0; $last = $sz }
    if ($stable -ge 6 -and $sz -gt 0) { break }
}
W ("xspice log size=" + $last + " after " + [math]::Round(((Get-Date)-$t0).TotalSeconds,1) + "s")

# look for visible Multisim windows (Grapher etc.)
$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if ($mp) {
    $pid_ = $mp[0].Id
    $cb = [PL.W+EnumProc]{
        param($h, $p)
        $q = 0; [void][PL.W]::GetWindowThreadProcessId($h, [ref]$q)
        if ($q -eq $pid_ -and [PL.W]::IsWindowVisible($h)) {
            $sb = New-Object System.Text.StringBuilder 512; [void][PL.W]::GetWindowTextW($h, $sb, 512)
            $cb2 = New-Object System.Text.StringBuilder 128; [void][PL.W]::GetClassNameW($h, $cb2, 128)
            if ($sb.Length -gt 0) { W ("VISIBLE 0x{0:X} [{1}] '{2}'" -f [int64]$h, $cb2.ToString(), $sb.ToString()) }
        }
        return $true
    }
    [void][PL.W]::EnumWindows($cb, [IntPtr]::Zero)
}
W ("XSPICE log tail:")
if (Test-Path $xlog) { foreach ($l in (Get-Content $xlog | Select-Object -Last 30)) { W ("   " + $l) } }

$hold = [int]$env:MS_HOLD
W ("holding Multisim open for $hold s (state=" + $c.SimulationState + " err='" + $c.LastErrorMessage + "')")
Start-Sleep -Seconds $hold
try { $a.Disconnect() } catch {}
W "plot run done"
