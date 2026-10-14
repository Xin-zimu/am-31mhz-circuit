# ASCII-only. Focus Multisim main window, send a key, report visible dialogs + NiCds changes.
# env: MS_DEBUGDIR, MS_NICDS, MS_KEYS, MS_SECS
$ErrorActionPreference = 'Continue'
Add-Type -Namespace U6 -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 1024; [void][U6.W]::GetWindowTextW($h, $sb, 1024); return $sb.ToString() }
function C([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 256; [void][U6.W]::GetClassNameW($h, $sb, 256); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { Write-Output "multisim not running"; exit }
$pid_ = [uint32]$mp[0].Id
Write-Output "pid=$pid_"

$script:vis = New-Object System.Collections.ArrayList
$cb = [U6.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][U6.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_ -and [U6.W]::IsWindowVisible($h)) {
        $t = T $h
        if ($t) { [void]$script:vis.Add([pscustomobject]@{H=$h; T=$t; C=(C $h)}) }
    }
    return $true
}
[void][U6.W]::EnumWindows($cb, [IntPtr]::Zero)
Write-Output ("visible titled windows: " + $script:vis.Count)
foreach ($w in $script:vis) { Write-Output ("  hwnd=0x{0:X} [{1}] '{2}'" -f [int64]$w.H, $w.C, $w.T) }

$main = $script:vis | Where-Object { $_.T -like '*Multisim*' } | Select-Object -First 1
if (-not $main) { Write-Output "no Multisim main frame found"; exit }
Write-Output ("targeting 0x{0:X} '{1}'" -f [int64]$main.H, $main.T)
[void][U6.W]::ShowWindow($main.H, 9)
Start-Sleep -Milliseconds 500
[void][U6.W]::SetForegroundWindow($main.H)
Start-Sleep -Milliseconds 800
$fg = [U6.W]::GetForegroundWindow()
Write-Output ("foreground now 0x{0:X} '{1}'" -f [int64]$fg, (T $fg))

$nicds = $env:MS_NICDS
$before = @{}
if (Test-Path $nicds) { Get-ChildItem $nicds -File | ForEach-Object { $before[$_.FullName] = $_.Length } }

$ws = New-Object -ComObject WScript.Shell
Write-Output ("sending: " + $env:MS_KEYS)
$ws.SendKeys($env:MS_KEYS)

$deadline = (Get-Date).AddSeconds([int]$env:MS_SECS)
$seen = @{}
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if (Test-Path $nicds) {
        foreach ($f in (Get-ChildItem $nicds -File)) {
            $prev = -1; if ($before.ContainsKey($f.FullName)) { $prev = $before[$f.FullName] }
            if ($f.Length -ne $prev) { Write-Output ("NICDS {0}: {1} -> {2}" -f $f.Name, $prev, $f.Length); $before[$f.FullName] = $f.Length }
        }
    }
    $script:dial = New-Object System.Collections.ArrayList
    $cb2 = [U6.W+EnumProc]{
        param($h, $p)
        $q = 0; [void][U6.W]::GetWindowThreadProcessId($h, [ref]$q)
        $c = C $h
        if ([U6.W]::IsWindowVisible($h) -and ($q -eq $pid_ -or $c -eq '#32768')) {
            $t = T $h
            if ($c -eq '#32770' -or $c -eq '#32768') { [void]$script:dial.Add([pscustomobject]@{H=$h; T=$t; C=$c}) }
        }
        return $true
    }
    [void][U6.W]::EnumWindows($cb2, [IntPtr]::Zero)
    foreach ($d in $script:dial) {
        $k = "{0:X}|{1}" -f [int64]$d.H, $d.T
        if (-not $seen.ContainsKey($k)) {
            $seen[$k] = $true
            $kids = ''
            $cb3 = [U6.W+EnumProc]{ param($c2, $p2)
                $cc = C $c2; $ct = T $c2
                if ($ct -and ($cc -match 'Static|Button|Edit')) { $script:kids += (" [" + $cc + "]" + $ct) }
                return $true }
            $script:kids = ''
            [void][U6.W]::EnumChildWindows($d.H, $cb3, [IntPtr]::Zero)
            Write-Output ("DLG [{0}] '{1}'{2}" -f $d.C, $d.T, $script:kids)
        }
    }
    $p2 = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
    if (-not $p2) { Write-Output "*** multisim GONE"; break }
}
Write-Output "done"
