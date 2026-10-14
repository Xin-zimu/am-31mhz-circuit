# ASCII-only. List InvokePattern-capable UIA elements under the Multisim main window.
# env: MS_DEBUGDIR, MS_MAIN_TITLE_FILTER, MS_CAP
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -Namespace U7 -Name W -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr p);
'@
$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir 'uia_invoke.txt'
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("start " + (Get-Date)) -Encoding UTF8
function T([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 1024; [void][U7.W]::GetWindowTextW($h, $sb, 1024); return $sb.ToString() }
function C([IntPtr]$h) { $sb = New-Object System.Text.StringBuilder 256; [void][U7.W]::GetClassNameW($h, $sb, 256); return $sb.ToString() }

$mp = Get-Process -Name multisim -ErrorAction SilentlyContinue
if (-not $mp) { W "multisim not running"; exit }
$pid_ = $mp[0].Id
$script:main = [IntPtr]::Zero
$cb = [U7.W+EnumProc]{
    param($h, $p)
    $q = 0; [void][U7.W]::GetWindowThreadProcessId($h, [ref]$q)
    if ($q -eq $pid_ -and [U7.W]::IsWindowVisible($h)) {
        $t = T $h
        if ($t -like '*Multisim*') { $script:main = $h }
    }
    return $true
}
[void][U7.W]::EnumWindows($cb, [IntPtr]::Zero)
W ("pid=$pid_ main=0x" + ([int64]$script:main).ToString('X'))
if ($script:main -eq [IntPtr]::Zero) { exit }

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$el = $AE::FromHandle($script:main)
$all = $el.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
W ("descendants: " + $all.Count)
$cap = [int]$env:MS_CAP
$n = 0
foreach ($e in $all) {
    if ($n -ge $cap) { W "...cap reached"; break }
    $n++
    try {
        $ct = $e.Current.ControlType.ProgrammaticName.Replace('ControlType.','')
        $nm = $e.Current.Name
        $aid = $e.Current.AutomationId
        $r = $e.Current.BoundingRectangle
        $pats = ''
        try { if ($e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)) { $pats += 'INVOKE ' } } catch {}
        try { if ($e.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)) { $pats += 'EXPAND ' } } catch {}
        try { if ($e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)) { $pats += 'SEL ' } } catch {}
        if ($pats -or $ct -match 'Menu|Button|ToolBar|Tab') {
            W ("{0} aid='{1}' [{2}] {3} rect=({4:F0},{5:F0},{6:F0},{7:F0}) name='{8}'" -f $pats, $aid, $ct, '', $r.X, $r.Y, $r.Width, $r.Height, $nm)
        }
    } catch {}
}
W "done"
