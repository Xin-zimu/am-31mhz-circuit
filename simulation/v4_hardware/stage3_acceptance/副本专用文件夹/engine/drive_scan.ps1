param([string]$Eng,[string]$Runner,[string]$Manifest)
$ErrorActionPreference='Continue'
$man = Get-Content $Manifest -Raw | ConvertFrom-Json
$res = @()
foreach ($name in $man.cases.PSObject.Properties.Name) {
  $raw = Join-Path $Eng ($name + ".raw")
  if (Test-Path $raw) { Remove-Item $raw -Force }
  try {
    $out = & $Runner -CmdFile (Join-Path $Eng ($name + ".cmd")) -LogFile (Join-Path $Eng ($name + ".log")) -RawFile $raw -TimeoutSeconds 300
    $res += ($name + " " + ($out -join " "))
  } catch { $res += ($name + " EXC " + $_.Exception.Message) }
}
$res -join [char]10