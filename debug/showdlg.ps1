# ASCII-only. Show a hidden Multisim dialog by title substring and dump its controls.
# env: MS_DEBUGDIR, MS_WIN_FILTER
$ErrorActionPreference = 'Continue'
Add-Type -Namespace U8 -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
[DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 2048; [void][U8.W]::GetWindowTextW($h, $sb, 2048); return $sb.ToString() }
function C([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 256; [void][U8.W]::GetClassNameW($h, $sb, 256); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { Write-Output "multisim not running"; exit }
$pid_ = $mp[0].Id
$filt = $env:MS_WIN_FILTER
$script:target = [IntPtr]::Zero
$cb = [U8.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][U8.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_) { $t = T $h; if ($t -like ("*" + $filt + "*")) { $script:target = $h; Write-Output ("FOUND 0x{0:X} '{1}' vis={2}" -f [int64]$h, $t, [U8.W]::IsWindowVisible($h)) } }
    return $true
}
[void][U8.W]::EnumWindows($cb, [IntPtr]::Zero)
if ($script:target -eq [IntPtr]::Zero) { Write-Output "target not found"; exit }

[void][U8.W]::ShowWindow($script:target, 5)
Start-Sleep -Milliseconds 600
[void][U8.W]::SetForegroundWindow($script:target)
Start-Sleep -Milliseconds 600
Write-Output ("after show: vis=" + [U8.W]::IsWindowVisible($script:target))
$cb2 = [U8.W+EnumProc]{
    param($h, $p)
    Write-Output ("  id={0} en={1} vis={2} [{3}] '{4}'" -f [U8.W]::GetDlgCtrlID($h), [U8.W]::IsWindowEnabled($h), [U8.W]::IsWindowVisible($h), (C $h), (T $h))
    return $true
}
[void][U8.W]::EnumChildWindows($script:target, $cb2, [IntPtr]::Zero)
Write-Output "done"
