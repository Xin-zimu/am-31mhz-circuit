param([string]$InputFile,[string]$Prefix)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.OpenFile($InputFile)
 Write-Output ('OPEN '+$c.CircuitName)
 $c.ReportNetlist($false,0,$Prefix+'.net.txt') | Out-Null
 Write-Output ('OUTPUTS '+(@($c.EnumOutputs(1)) -join ','))
} finally {$a.Disconnect()}
