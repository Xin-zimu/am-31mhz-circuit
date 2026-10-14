param([string]$InputFile,[string]$OutputFile)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.OpenFile($InputFile)
 Write-Output ($c.ReplaceComponent('RPU1','A',0,'Analog','COMPARATOR','LM393P','LM393/TI'))
 Write-Output ('SAVE '+$c.SaveAs($OutputFile))
} catch {Write-Output $_;Write-Output $c.LastErrorMessage} finally {$a.Disconnect()}
