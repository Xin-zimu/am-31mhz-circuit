param([string]$InputFile,[string]$OutputFile)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.OpenFile($InputFile)
 Write-Output ('COMPONENTS '+(@($c.EnumComponents(0)) -join ','))
 Write-Output ('SAVE '+$c.SaveAs($OutputFile))
 $c.ReportNetlist($false,0,$OutputFile+'.net.txt') | Out-Null
} finally {$a.Disconnect()}
