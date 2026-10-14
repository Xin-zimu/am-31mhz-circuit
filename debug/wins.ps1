# ASCII-only. List top-level windows of multisim.exe, then UIA-dump the ones matching a filter.
# env: MS_DEBUGDIR, MS_UIA_FILTER (substring, optional), MS_MAXDEPTH
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -Namespace U3 -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'wins.txt'
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("wins start " + (Get-Date)) -Encoding UTF8

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running"; exit }
$pid_ = $mp[0].Id
W ("multisim pid=$pid_")

$script:list = New-Object System.Collections.ArrayList
$cb = [U3.W+EnumProc]{
    param($hh, $pp)
    $p = 0; [void][U3.W]::GetWindowThreadProcessId($hh, [ref]$p)
    if ($p -eq $pid_) {
        $sb = New-Object System.Text.StringBuilder 512
        [void][U3.W]::GetWindowTextW($hh, $sb, 512)
        $cb2 = New-Object System.Text.StringBuilder 256
        [void][U3.W]::GetClassNameW($hh, $cb2, 256)
        [void]$script:list.Add([pscustomobject]@{H=$hh; T=$sb.ToString(); C=$cb2.ToString(); V=[U3.W]::IsWindowVisible($hh)})
    }
    return $true
}
[void][U3.W]::EnumWindows($cb, [IntPtr]::Zero)
W ("top-level windows: " + $script:list.Count)
foreach ($w in $script:list) {
    W ("  hwnd=0x{0:X} vis={1} [{2}] '{3}'" -f [int64]$w.H, $w.V, $w.C, $w.T)
}

$filt = $env:MS_UIA_FILTER
if (-not $filt) { W "no filter; done"; exit }
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$maxd = [int]$env:MS_MAXDEPTH
function Dump($e, [int]$d) {
    if ($d -gt $maxd) { return }
    try { W (('  ' * $d) + "<" + $e.Current.ControlType.ProgrammaticName.Replace('ControlType.','') + "> aid='" + $e.Current.AutomationId + "' name='" + $e.Current.Name + "'") } catch { return }
    try { foreach ($k in $e.FindAll($TS::Children, [System.Windows.Automation.Condition]::TrueCondition)) { Dump $k ($d + 1) } } catch {}
}
foreach ($w in $script:list) {
    if ($w.T -notlike ("*" + $filt + "*")) { continue }
    W ("================ UIA DUMP '" + $w.T + "'")
    try { Dump ($AE::FromHandle($w.H)) 0 } catch { W ("uia err " + $_.Exception.Message) }
}
W "wins done"
