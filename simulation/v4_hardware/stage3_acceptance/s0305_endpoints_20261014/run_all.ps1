param([string[]]$Tags=@(),[switch]$ContinueOnFailure)
$ErrorActionPreference='Stop'
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'run_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$ps32='C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
if($Tags.Count -eq 0){$Tags=@($manifest.cases | ForEach-Object {$_.tag})}
$failed=@()
foreach($runTag in $Tags){
  Write-Output ('RUNNING '+$runTag)
  & $ps32 -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_one.ps1') -Tag $runTag
  if($LASTEXITCODE -ne 0){
    $failed+= $runTag
    if(-not $ContinueOnFailure){throw ('Stopped after failed case '+$runTag)}
    Write-Output ('FAILED; continuing independent case after fresh preflight: '+$runTag)
  }
}
if($failed.Count -gt 0){Write-Output ('FAILED CASES: '+($failed -join ', '));exit 1}
Write-Output 'ALL REQUESTED CASES COMPLETED'
