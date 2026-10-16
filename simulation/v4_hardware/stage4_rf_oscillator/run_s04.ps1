param([Parameter(Mandatory=$true)][string]$BasePath,[int]$TimeoutSeconds=120)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath ($BasePath+'.raw')) {throw 'Existing raw output: choose a new run name.'}
if((Test-Path -LiteralPath ($BasePath+'.log')) -or (Test-Path -LiteralPath ($BasePath+'.status.json'))) {throw 'Existing attempt evidence: choose a new run name.'}
$s04App=New-Object -ComObject MultisimInterface.MultisimApp
$s04App.Path='D:\multimism\Circuit Design Suite 14.3\multisim.exe'
$s04App.Connect()
$s04Timer=[Diagnostics.Stopwatch]::StartNew()
try {
  $s04Circuit=$s04App.NewFile()
  $s04Circuit.DoCommandLine(($BasePath+'.cmd'),($BasePath+'.log'))
  while($s04Timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    Start-Sleep -Milliseconds 200
    if($s04Circuit.SimulationState -eq 0 -and (Test-Path -LiteralPath ($BasePath+'.raw'))) {break}
    if($s04Circuit.LastErrorMessage) {break}
    if($s04Circuit.SimulationState -eq 0 -and (Test-Path -LiteralPath ($BasePath+'.log')) -and (Select-String -LiteralPath ($BasePath+'.log') -Pattern '^Error:' -Quiet -ErrorAction SilentlyContinue)) {break}
  }
  $s04LogErrors=@()
  if(Test-Path -LiteralPath ($BasePath+'.log')) {$s04LogErrors=@(Select-String -LiteralPath ($BasePath+'.log') -Pattern '^Error:' -ErrorAction SilentlyContinue | ForEach-Object {$_.Line})}
  $s04Status=[ordered]@{seconds=$s04Timer.Elapsed.TotalSeconds;state=$s04Circuit.SimulationState;last_error=$s04Circuit.LastErrorMessage;log_errors=$s04LogErrors;output_exists=(Test-Path -LiteralPath ($BasePath+'.raw'))}
  $s04Status | ConvertTo-Json | Set-Content -LiteralPath ($BasePath+'.status.json') -Encoding UTF8
  $s04Status | ConvertTo-Json
  if(-not $s04Status.output_exists -or $s04Status.last_error -or $s04Status.state -ne 0 -or $s04LogErrors.Count -gt 0) {throw 'Simulation incomplete or failed; inspect status/log.'}
} finally {$s04App.Disconnect()}
