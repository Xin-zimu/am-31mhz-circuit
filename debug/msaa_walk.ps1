# ASCII-only. MSAA walker for the Multisim main window; can invoke a named menu item.
# env: MS_DEBUGDIR, MS_DEPTH, MS_INVOKE (substring) or MS_LIST
$ErrorActionPreference = 'Continue'
Add-Type -Namespace MB -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr hwnd, uint dwId, ref Guid riid, [MarshalAs(UnmanagedType.Interface)] ref object ppvObject);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$out = Join-Path $env:MS_DEBUGDIR 'msaa_walk.txt'
function W([string]$m) { Write-Output $m; Add-Content -LiteralPath $out -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $out -Value ("msaa_walk " + (Get-Date)) -Encoding UTF8
function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 512; [void][MB.W]::GetWindowTextW($h, $sb, 512); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running"; exit }
$pid_ = $mp[0].Id
$script:main = [IntPtr]::Zero
$cb = [MB.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][MB.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_ -and [MB.W]::IsWindowVisible($h)) { $t = T $h; if ($t -like '*Multisim*') { $script:main = $h } }
    return $true
}
[void][MB.W]::EnumWindows($cb, [IntPtr]::Zero)
W ("main=0x" + ([int64]$script:main).ToString('X'))
if ($script:main -eq [IntPtr]::Zero) { exit }

$IID = [Guid]'618736E0-3C3D-11CF-810C-00AA00389B71'
$raw = $null
[void][MB.W]::AccessibleObjectFromWindow($script:main, [uint32]4294967292, [ref]$IID, [ref]$raw)
if ($null -eq $raw) { W "no accessible"; exit }

$script:found = New-Object System.Collections.ArrayList
function Walk($a, [int]$d, [string]$path) {
    if ($d -gt [int]$env:MS_DEPTH) { return }
    $n = ''; $r = ''; $s = ''
    try { $n = $a.accName(0) } catch {}
    try { $r = $a.accRole(0) } catch {}
    try { $s = $a.accState(0) } catch {}
    W (('  ' * $d) + "role=$r state=$s name='$n'")
    [void]$script:found.Add([pscustomobject]@{Obj=$a; Name=$n; Role=$r; Path=$path})
    $cc = 0
    try { $cc = $a.accChildCount } catch {}
    for ($i = 1; $i -le $cc; $i++) {
        $c = $null
        try { $c = $a.accChild($i) } catch { }
        if ($null -ne $c) { Walk $c ($d + 1) ($path + '/' + $n + '#' + $i) }
        else {
            $cn = ''; $cr = ''
            try { $cn = $a.accName($i) } catch {}
            try { $cr = $a.accRole($i) } catch {}
            W (('  ' * ($d+1)) + "leaf role=$cr name='$cn' (idx $i)")
            [void]$script:found.Add([pscustomobject]@{Obj=$a; Name=$cn; Role=$cr; Path=$path; Idx=$i})
        }
    }
}
Walk $raw 0 ''
W ("total nodes: " + $script:found.Count)

$inv = $env:MS_INVOKE
if ($inv) {
    $t = $script:found | Where-Object { $_.Name -like ("*" + $inv + "*") } | Select-Object -First 1
    if ($null -eq $t) { W ("no node matching '" + $inv + "'") }
    else {
        W ("invoking '" + $t.Name + "' role=" + $t.Role)
        try { $t.Obj.accDoDefaultAction([int]$t.Idx); W "invoke ok" } catch { W ("invoke ERR " + $_.Exception.Message) }
    }
}
W "msaa_walk done"
