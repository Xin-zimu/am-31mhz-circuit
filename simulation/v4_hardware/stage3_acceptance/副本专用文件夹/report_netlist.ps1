# Authoritative check: report the netlist Multisim actually builds for a project.
param([string]$Project,[string]$Out)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('OPENED ' + $c.CircuitName + ' comps=' + (@($c.EnumComponents(0)).Count))
  $c.ReportNetlist($false,0,$Out) | Out-Null
  Write-Output ('netlist=' + $Out + ' bytes=' + (Get-Item $Out).Length)
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'