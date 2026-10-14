# ASCII-only. Activate Multisim, send a key, then watch for dialogs and new result files.
# env: MS_DEBUGDIR, MS_KEYS (SendKeys), MS_SECS, MS_NICDS
$ErrorActionPreference = 'Continue'
Add-Type -Namespace U5 -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'rungui.txt'
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("rungui start " + (Get-Date)) -Encoding UTF8

function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 1024; [void][U5.W]::GetWindowTextW($h, $sb, 1024); return $sb.ToString() }
function C([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 256; [void][U5.W]::GetClassNameW($h, $sb, 256); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running"; exit }
$pid_ = $mp[0].Id
W ("pid=$pid_")

# find the main frame (visible top-level with 'Multisim' in title)
$script:main = [IntPtr]::Zero
$cb = [U5.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][U5.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_ -and [U5.W]::IsWindowVisible($h)) {
        $t = T $h; $c = C $h
        if ($t -like '*Multisim*' -and $c -match 'Multisim14|LVFrame') { $script:main = $h; W ("main frame 0x{0:X} [{1}] '{2}'" -f [int64]$h, $c, $t) }
    }
    return $true
}
if ($script:main -eq [IntPtr]::Zero) {
    $cb2 = [U5.W+EnumProc]{ param($h, $p)
        $q = 0; [void][U5.W]::GetWindowThreadProcessId($h, [ref]$q)
        if ($q -eq $pid_ -and [U5.W]::IsWindowVisible($h)) { $t = T $h; if ($t) { W ("visible 0x{0:X} [{1}] '{2}'" -f [int64]$h, (C $h), $t) } }
        return $true }
    [void][U5.W]::EnumWindows($cb2, [IntPtr]::Zero)
} else {
    [void][U5.W]::SetForegroundWindow($script:main)
}
[void][U5.W]::EnumWindows($cb, [IntPtr]::Zero)

$nicds = $env:MS_NICDS
$before = @{}
if (Test-Path $nicds) { Get-ChildItem $nicds -File | ForEach-Object { $before[$_.FullName] = $_.Length } }

$ws = New-Object -ComObject WScript.Shell
Start-Sleep -Milliseconds 800
W ("sending keys: " + $env:MS_KEYS)
$ws.SendKeys($env:MS_KEYS)

$deadline = (Get-Date).AddSeconds([int]$env:MS_SECS)
$seen = @{}
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    # new/changed files in NiCds
    if (Test-Path $nicds) {
        foreach ($f in (Get-ChildItem $nicds -File)) {
            $prev = -1; if ($before.ContainsKey($f.FullName)) { $prev = $before[$f.FullName] }
            if ($f.Length -ne $prev) { W ("NICDS {0} len {1} -> {2}" -f $f.Name, $prev, $f.Length); $before[$f.FullName] = $f.Length }
        }
    }
    # visible dialogs of multisim
    $cb3 = [U5.W+EnumProc]{
        param($h, $p)
        $q = 0; [void][U5.W]::GetWindowThreadProcessId($h, [ref]$q)
        if ($q -eq $pid_ -and [U5.W]::IsWindowVisible($h) -and (C $h) -eq '#32770') {
            $key = "{0:X}" -f [int64]$h
            $ttl = T $h
            $kids = ''
            $cb4 = [U5.W+EnumProc]{ param($c2, $p2)
                $cc = C $c2; $ct = T $c2
                if ($ct -and ($cc -match 'Static|Button|Edit|SysTreeView')) { $script:kids += (" [" + $cc + "]" + $ct) }
                return $true }
            $script:kids = ''
            [void][U5.W]::EnumChildWindows($h, $cb4, [IntPtr]::Zero)
            if (-not $seen.ContainsKey($key + $ttl + $script:kids)) {
                $seen[$key + $ttl + $script:kids] = $true
                W ("DIALOG 0x" + $key + " '" + $ttl + "'" + $script:kids)
            }
        }
        return $true }
    $script:kids = ''
    [void][U5.W]::EnumWindows($cb3, [IntPtr]::Zero)
    $p2 = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
    if (-not $p2) { W "*** multisim process GONE"; break }
    if (-not $p2.Responding) { W "*** multisim NOT RESPONDING" }
}
W "rungui done"
