$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
Write-Output ('connected=' + $a.IsConnected + ' ver=' + $a.VersionInfo)
Write-Output ('bitness=' + [IntPtr]::Size)
$a.Disconnect()
Write-Output 'done'
