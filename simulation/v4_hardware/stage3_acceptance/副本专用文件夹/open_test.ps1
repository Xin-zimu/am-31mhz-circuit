$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
Write-Output ('connected=' + $a.IsConnected)
$files = @('D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹\roundtrip_TMAX1ns.ms14')
foreach($f in $files){
  try {
    $c=$a.OpenFile($f)
    Write-Output ('OPENED name=' + $c.CircuitName + ' comps=' + (@($c.EnumComponents(0)).Count) + ' state=' + $c.SimulationState)
    $c.ReportNetlist($false,0,($f + '.rt.net.txt')) | Out-Null
    Write-Output ('netlist bytes=' + (Get-Item ($f + '.rt.net.txt')).Length)
  } catch { Write-Output ('EXC ' + $_.Exception.Message) }
}
$a.Disconnect()
Write-Output 'done'