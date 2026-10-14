# ASCII-only. UI Automation dump of Multisim windows.
# env: MS_DEBUGDIR, MS_UIA_MODE (dump|menu), MS_UIA_FILTER (window name substring), MS_UIA_ITEM
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$outdir = $env:MS_DEBUGDIR
$logf   = Join-Path $outdir ("uia_" + $env:MS_UIA_MODE + ".txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("uia start " + (Get-Date)) -Encoding UTF8

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$proc = (Get-Process -Name multisim | Select-Object -First 1).Id
W ("multisim pid=$proc")
$cond = New-Object System.Windows.Automation.PropertyCondition($AE::ProcessIdProperty, $proc)
$wins = $AE::RootElement.FindAll($TS::Children, $cond)
W ("top-level windows: " + $wins.Count)

function Dump($el, [int]$d, [int]$maxd) {
    if ($d -gt $maxd) { return }
    try {
        $n = $el.Current.Name
        $ct = $el.Current.ControlType.ProgrammaticName
        $aid = $el.Current.AutomationId
        $off = $el.Current.IsOffscreen
        W (('  ' * $d) + "<" + $ct.Replace('ControlType.','') + "> aid='" + $aid + "' off=" + $off + " name='" + $n + "'")
    } catch { return }
    try {
        $kids = $el.FindAll($TS::Children, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($k in $kids) { Dump $k ($d + 1) $maxd }
    } catch {}
}

foreach ($w in $wins) {
    $nm = ''
    try { $nm = $w.Current.Name } catch {}
    $filt = $env:MS_UIA_FILTER
    if ($filt -and $nm -notlike ("*" + $filt + "*")) { continue }
    W ("================ WINDOW '" + $nm + "'")
    Dump $w 0 6
}
W "uia done"
