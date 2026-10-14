# ASCII-only. UIA dump of a specific (possibly hidden) Multisim dialog found by exact title.
# env: MS_DEBUGDIR, MS_TITLE, MS_MAXDEPTH
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -Namespace U2 -Name W -MemberDefinition @'
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowW(string cls, string title);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
'@

$outdir = $env:MS_DEBUGDIR
$title  = $env:MS_TITLE
$logf   = Join-Path $outdir ("uiawin.txt")
function W([string]$m) {
    $line = "{0} | {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $m
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}
Set-Content -LiteralPath $logf -Value ("uiawin start " + (Get-Date) + " title=" + $title) -Encoding UTF8

$h = [U2.W]::FindWindowW($null, $title)
W ("FindWindow('" + $title + "') -> 0x" + ([int64]$h).ToString('X'))
if ($h -eq [IntPtr]::Zero) { W "not found"; exit }

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$el = $AE::FromHandle($h)
W ("element name='" + $el.Current.Name + "' type=" + $el.Current.ControlType.ProgrammaticName)

$maxd = [int]$env:MS_MAXDEPTH
function Dump($e, [int]$d) {
    if ($d -gt $maxd) { return }
    try {
        W (('  ' * $d) + "<" + $e.Current.ControlType.ProgrammaticName.Replace('ControlType.','') + "> aid='" + $e.Current.AutomationId + "' name='" + $e.Current.Name + "'")
    } catch { return }
    try {
        $kids = $e.FindAll($TS::Children, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($k in $kids) { Dump $k ($d + 1) }
    } catch {}
}
Dump $el 0
W "uiawin done"
