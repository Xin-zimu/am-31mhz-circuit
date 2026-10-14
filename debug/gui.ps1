# ASCII-only. Win32 window recon + dialog text reader for Multisim.
# env: MS_DEBUGDIR, MS_DEBUG, MS_EXE, MS_MODE (recon|run), MS_SECS
$ErrorActionPreference = 'Continue'
$outdir = $env:MS_DEBUGDIR
$mode   = $env:MS_MODE
$logf   = Join-Path $outdir ("gui_" + $mode + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("gui start " + (Get-Date) + " mode=" + $mode) -Encoding UTF8

Add-Type -Namespace U -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@

function Get-Text([IntPtr]$h) {
    $sb = New-Object System.Text.StringBuilder 1024
    [void][U.W]::GetWindowTextW($h, $sb, 1024)
    return $sb.ToString()
}
function Get-Class([IntPtr]$h) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][U.W]::GetClassNameW($h, $sb, 256)
    return $sb.ToString()
}
$script:nodes = New-Object System.Collections.ArrayList
function Walk([IntPtr]$h, [int]$d) {
    $cls = Get-Class $h; $txt = Get-Text $h
    $pid_ = 0; [void][U.W]::GetWindowThreadProcessId($h, [ref]$pid_)
    $vis = [U.W]::IsWindowVisible($h)
    $id  = [U.W]::GetDlgCtrlID($h)
    [void]$script:nodes.Add([pscustomobject]@{H=$h; D=$d; Cls=$cls; Txt=$txt; Pid=$pid_; Vis=$vis; Id=$id})
    $cb = [U.W+EnumProc]{ param($c, $p) Walk $c ($d+1); return $true }
    [void][U.W]::EnumChildWindows($h, $cb, [IntPtr]::Zero)
}
function Dump-All([string]$why) {
    $script:nodes.Clear()
    $cb = [U.W+EnumProc]{ param($c, $p) Walk $c 0; return $true }
    [void][U.W]::EnumWindows($cb, [IntPtr]::Zero)
    W ("---- window tree (" + $why + ") ----")
    foreach ($n in $script:nodes) {
        if ($n.Pid -eq $script:mspid -or $n.Cls -eq '#32770') {
            W ("{0}{1} hwnd=0x{2:X} pid={3} vis={4} id={5} [{6}] '{7}'" -f ('  ' * $n.D), '|', [int64]$n.H, $n.Pid, $n.Vis, $n.Id, $n.Cls, $n.Txt)
        }
    }
}

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running; starting via COM"; $startNew = $true } else { $script:mspid = $mp[0].Id; W ("multisim already running pid=" + $script:mspid) }

if ($startNew) {
    $a = New-Object -ComObject MultisimInterface.MultisimApp
    $a.Path = $env:MS_EXE
    $a.Connect()
    $c = $a.OpenFile($env:MS_DEBUG)
    W ("opened " + $c.CircuitName)
    Start-Sleep -Seconds 4
    $script:mspid = (Get-Process -Name multisim)[0].Id
}
W ("mspid=" + $script:mspid)
Dump-All "initial"

if ($mode -eq 'run') {
    $main = ($script:nodes | Where-Object { $_.Pid -eq $script:mspid -and $_.D -eq 0 -and $_.Vis -and $_.Txt -ne '' } | Select-Object -First 1)
    if ($main) { W ("activating '" + $main.Txt + "'"); [void][U.W]::SetForegroundWindow($main.H) }
    Start-Sleep -Milliseconds 700
    $ws = New-Object -ComObject WScript.Shell
    W "sending F5"
    $ws.SendKeys('{F5}')
    $deadline = (Get-Date).AddSeconds([int]$env:MS_SECS)
    $seen = @{}
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 900
        Dump-All "poll"
        foreach ($n in $script:nodes) {
            if ($n.Cls -eq '#32770' -and $n.D -eq 0 -and $n.Vis) {
                $key = "{0:X}" -f [int64]$n.H
                if (-not $seen.ContainsKey($key)) {
                    $seen[$key] = $true
                    W ("*** DIALOG 0x" + $key + " title='" + $n.Txt + "'")
                    foreach ($ch in ($script:nodes | Where-Object { $_.D -gt 0 })) { }
                }
            }
        }
        $p = Get-Process -Name multisim -ErrorAction SilentlyContinue
        if (-not $p) { W "*** multisim process is GONE (crash)"; break }
    }
    W "run window done"
}
W "gui done"
