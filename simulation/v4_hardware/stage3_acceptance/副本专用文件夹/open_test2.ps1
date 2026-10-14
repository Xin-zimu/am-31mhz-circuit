$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
Write-Output ('connected=' + $a.IsConnected)
$f='D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹\roundtrip_TMAX1ns.ms14'
try {
  $c=$a.OpenFile($f)
  Write-Output ('OPENED name=' + $c.CircuitName + ' comps=' + (@($c.EnumComponents(0)).Count))
  $c.ReportNetlist($false,0,($f + '.net.txt')) | Out-Null
  Write-Output ('netlist bytes=' + (Get-Item ($f + '.net.txt')).Length)
} catch { Write-Output ('EXC ' + $_.Exception.Message) }
try{$a.Disconnect()}catch{}
Write-Output 'done'