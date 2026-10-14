param([string]$InputFile,[string]$Prefix)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.OpenFile($InputFile)
 Write-Output ('OPEN '+$c.CircuitName)
 Write-Output (@($c.EnumComponents(0)) -join ',')
 $c.ReportNetlist($false,0,$Prefix+'.net.txt') | Out-Null
 $c.Save() | Out-Null
 $c.GetCircuitImage(0,$Prefix+'.png') | Out-Null
} finally {$a.Disconnect()}
