# ASCII-only. MSAA (IAccessible) probe of the Multisim main window.
# env: MS_DEBUGDIR, MS_MSAA_DEPTH
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName Accessibility
Add-Type -Namespace MA -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr hwnd, uint dwId, ref Guid riid, [MarshalAs(UnmanagedType.Interface)] ref object ppvObject);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$out = Join-Path $env:MS_DEBUGDIR 'msaa.txt'
function W([string]$m) { Write-Output $m; Add-Content -LiteralPath $out -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $out -Value ("msaa " + (Get-Date)) -Encoding UTF8
function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 512; [void][MA.W]::GetWindowTextW($h, $sb, 512); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running"; exit }
$pid_ = $mp[0].Id
$script:main = [IntPtr]::Zero
$cb = [MA.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][MA.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_ -and [MA.W]::IsWindowVisible($h)) { $t = T $h; if ($t -like '*Multisim*') { $script:main = $h } }
    return $true
}
[void][MA.W]::EnumWindows($cb, [IntPtr]::Zero)
W ("pid=$pid_ main=0x" + ([int64]$script:main).ToString('X'))
if ($script:main -eq [IntPtr]::Zero) { exit }

$IID_IAccessible = [Guid]'618736E0-3C3D-11CF-810C-00AA00389B71'
foreach ($objid in @([uint32]0, [uint32]4294967292)) {
    $raw = $null
    $hr = [MA.W]::AccessibleObjectFromWindow($script:main, $objid, [ref]$IID_IAccessible, [ref]$raw)
    W ("objid=0x{0:X} hr=0x{1:X} raw={2}" -f $objid, $hr, ($null -ne $raw))
    if ($null -eq $raw) { continue }
    $acc = $raw
    try { W ("  members: " + (($acc | Get-Member -MemberType Property,Method | Select-Object -ExpandProperty Name) -join ',')) } catch {}
    try {
        $cc = $acc.accChildCount
        W ("  name='" + $acc.accName(0) + "' role=" + $acc.accRole(0) + " children=" + $cc)
        for ($i = 1; $i -le [Math]::Min($cc, 60); $i++) {
            try {
                $n = $acc.accName($i); $r = $acc.accRole($i)
                $st = ''
                try { $st = $acc.accState($i) } catch {}
                W ("   [$i] role=$r state=$st name='$n'")
            } catch { }
        }
    } catch { W ("  walk err " + $_.Exception.Message) }
}
W "msaa done"
