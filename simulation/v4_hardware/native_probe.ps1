param([string]$File,[string]$OutDir)
$ErrorActionPreference='Stop'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
 $c=$a.OpenFile($File)
 Write-Output ('OPEN '+$c.CircuitName)
 Write-Output (@($c.EnumComponents(0)) -join ',')
 Write-Output ('OUTPUTS '+(@($c.EnumOutputs(1)) -join ','))
 $c.RunSimulation(0.0002,$true)
 Start-Sleep -Seconds 20
 Write-Output ('STATE '+$c.SimulationState+' ERROR '+$c.LastErrorMessage)
} finally {$a.Disconnect()}
