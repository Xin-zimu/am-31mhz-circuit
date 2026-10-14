# Bounded-retry batch driver for the S03-05 long-window make-up runs.
#
# Fixed policy (user-set, 2026-10-15):
#   * baseline case (C4 nominal)  : at most 2 attempts
#   * every other case            : at most 3 attempts
#   * every attempt is preserved; exhausted budget is recorded as budget_limited
#   * a single baseline success proves only "this run was computable";
#     it must NOT be reported as "the environment has recovered"
#   * no pass is presupposed for 5 ms or 7 ms; the frozen repeatability screen
#     and drift trend must be reported for whatever succeeds
#
# Attempt labels use fresh _b1/_b2/_b3 tags so that no existing .raw/.log/status
# is ever overwritten (run_one.ps1 refuses overwrite by design).

param(
  [Parameter(Mandatory=$true)][string]$Queue,
  [int]$TimeoutSeconds = 1800
)
$ErrorActionPreference = 'Stop'
$runRoot = 'D:\ms_xsp\stage3_acceptance\s0305_endpoints_20261014'
$ps32 = 'C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'

$queues = @{
  # batch 1: nominal baseline, precharged 5 ms tail, original configuration
  'baseline' = @(
    @{ case='C4'; tags=@('C4_4Vpp_D50_5ms_b1','C4_4Vpp_D50_5ms_b2'); max=2 }
  )
  # batch 2: the four endpoints, same precharged 5 ms tail condition
  'endpoints' = @(
    @{ case='C1'; tags=@('C1_1Vpp_D10_5ms_b1','C1_1Vpp_D10_5ms_b2','C1_1Vpp_D10_5ms_b3'); max=3 },
    @{ case='C3'; tags=@('C3_4Vpp_D10_5ms_b1','C3_4Vpp_D10_5ms_b2','C3_4Vpp_D10_5ms_b3'); max=3 },
    @{ case='C6'; tags=@('C6_4Vpp_D30_5ms_b1','C6_4Vpp_D30_5ms_b2','C6_4Vpp_D30_5ms_b3'); max=3 },
    @{ case='C7'; tags=@('C7_3Vpp_D50_5ms_b1','C7_3Vpp_D50_5ms_b2','C7_3Vpp_D50_5ms_b3'); max=3 }
  )
  # batch 3: C2 bias-convergence probe, 7 ms integration, last 0.5 ms saved
  'c2_7ms' = @(
    @{ case='C2'; tags=@('C2_1Vpp_D50_7ms_b1','C2_1Vpp_D50_7ms_b2','C2_1Vpp_D50_7ms_b3'); max=3 }
  )
  # batch 4: C2's paired 4 Vpp reference at the same 7 ms endpoint (linearity),
  #          also serving as the same-endpoint comparison for C7
  'c4_7ms' = @(
    @{ case='C4'; tags=@('C4_4Vpp_D50_7ms_b1','C4_4Vpp_D50_7ms_b2','C4_4Vpp_D50_7ms_b3'); max=3 }
  )
}

if (-not $queues.ContainsKey($Queue)) { throw ('Unknown queue: ' + $Queue) }

# Preflight: no Multisim may be running before the batch starts.
$pre = @(Get-Process -Name multisim -ErrorAction SilentlyContinue)
if ($pre.Count -gt 0) { throw ('Preflight rejected: existing Multisim PIDs ' + ($pre.Id -join ',')) }

$results = @()
foreach ($case in $queues[$Queue]) {
  $outcome = 'budget_limited'
  $used = 0
  $aborted = $false
  foreach ($t in $case.tags) {
    $used++
    $cmd = Join-Path $runRoot ($t + '.cmd')
    if (-not (Test-Path -LiteralPath $cmd)) {
      $results += [ordered]@{ case=$case.case; status='MISSING_CMD'; tag=$t }
      break
    }
    Write-Output ('ATTEMPT ' + $case.case + ' ' + $t + ' (' + $used + '/' + $case.max + ')')
    # run_one.ps1 lives next to this driver (the workspace), NOT in $runRoot:
    # the runtime dir holds only netlists, command files and raw/log output.
    & $ps32 -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_one.ps1') -Tag $t -TimeoutSeconds $TimeoutSeconds
    $rc = $LASTEXITCODE
    if ($rc -eq 0) {
      $outcome = 'COMPLETED'
      $results += [ordered]@{ case=$case.case; status='COMPLETED'; tag=$t; attempts_used=$used; attempt_budget=$case.max }
      break
    }
    # Distinguish "the attempt really ran and failed" from "the runner never
    # launched". A launch failure must NOT burn the attempt budget.
    $statusPath = Join-Path $PSScriptRoot ($t + '_status.json')
    if (-not (Test-Path -LiteralPath $statusPath)) {
      $used--
      $results += [ordered]@{ case=$case.case; status='LAUNCH_FAILED'; tag=$t; attempts_used=0; attempt_budget=$case.max; exit_code=$rc }
      Write-Output ('  LAUNCH FAILED for ' + $t + ' (exit ' + $rc + '); no status file was created, so this does not count as an attempt')
      $aborted = $true
      break
    }
    Write-Output ('  attempt ' + $t + ' did not complete (exit ' + $rc + '); preserving it and continuing if budget remains')
  }
  if ($aborted) { continue }
  if ($outcome -ne 'COMPLETED') {
    $results += [ordered]@{ case=$case.case; status='BUDGET_LIMITED'; tag=$null; attempts_used=$used; attempt_budget=$case.max }
    Write-Output ('BUDGET LIMITED for ' + $case.case + ': ' + $used + ' attempts exhausted without a completed run')
  }
}

# Reusable evidence log, one JSON per batch invocation.
$stamp = [DateTime]::Now.ToString('yyyyMMdd_HHmmss')
$log = [ordered]@{
  queue        = $Queue
  started_utc  = [DateTime]::UtcNow.ToString('o')
  policy       = 'baseline<=2 attempts; others<=3 attempts; every attempt preserved; success proves only this run'
  preflight_multisim_count = $pre.Count
  results      = $results
  finished_utc = [DateTime]::UtcNow.ToString('o')
}
$logPath = Join-Path $PSScriptRoot ('batch_' + $Queue + '_' + $stamp + '.json')
$log | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Output ('BATCH LOG ' + $logPath)
$log | ConvertTo-Json -Depth 6 -Compress
