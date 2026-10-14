param([string]$File)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try { $c=$a.OpenFile($File); Write-Output ('OPENED ' + $c.CircuitName + ' comps=' + (@($c.EnumComponents(0)).Count + 0)) }
catch { Write-Output ('EXC ' + $_.Exception.Message) }
try{$a.Disconnect()}catch{}
Write-Output 'done'