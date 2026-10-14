$title='Codex API probe'
$apath=Join-Path (Get-Location) 'api_probe'
$net=Join-Path $apath 'probe.cir'
[IO.File]::WriteAllText($net,"Codex API probe`r`nV1 IN 0 SIN(0 1 1k)`r`nR1 IN OUT 1k`r`nC1 OUT 0 100n`r`n.tran 1u 10m`r`n.end`r`n",[Text.Encoding]::ASCII)
$a=New-Object -ComObject MultisimInterface.MultisimApp
Write-Output ('PATH '+$a.Path+' CONNECTED '+$a.IsConnected)
$a.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$a.LogFile=Join-Path $apath 'multisim_api.log'
try {
 $a.Connect()
 Write-Output ('CONNECTED '+$a.IsConnected+' VERSION '+$a.VersionInfo)
 $c=$a.OpenFile($net)
 Write-Output ('OPENED '+$c.CircuitName+' FILE '+$c.FileName)
 Write-Output ('COMPONENTS '+($c.EnumComponents(0) -join ','))
 Write-Output ('OUTPUTS '+($c.EnumOutputs(0) -join ','))
 Write-Output ('SAVE '+$c.SaveAs((Join-Path $apath 'probe.ms14')))
 Write-Output ('LASTERROR '+$a.LastErrorMessage)
} catch { Write-Output ('ERROR '+$_); Write-Output ('LASTERROR '+$a.LastErrorMessage) } finally { if($a.IsConnected){$a.Disconnect()}; [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($a) }
