# Probe whether analysis settings (TSTOP/TMAX/TSTEP) are reachable as circuit parameters.
param([string]$Project)
$ErrorActionPreference='Continue'
$a=New-Object -ComObject MultisimInterface.MultisimApp
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.Connect()
try {
  $c=$a.OpenFile($Project)
  Write-Output ('name=' + $c.CircuitName)
  foreach($lvl in @(0,1)){
    try {
      $ps=@($c.EnumCircuitParameters($lvl))
      Write-Output ('level=' + $lvl + ' count=' + $ps.Count)
      $i=0
      foreach($p in $ps){
        $i++; if($i -gt 60){ Write-Output '  ...'; break }
        $v=''; try { $v = $c.CircuitParameterValue($p) } catch { $v='<err>' }
        Write-Output ('  [' + $lvl + '] ' + $p + ' = ' + $v)
      }
    } catch { Write-Output ('level ' + $lvl + ' ERR ' + $_.Exception.Message) }
  }
} catch { Write-Output ('EXC ' + $_.Exception.Message) } finally { try{$a.Disconnect()}catch{} }
Write-Output 'done'