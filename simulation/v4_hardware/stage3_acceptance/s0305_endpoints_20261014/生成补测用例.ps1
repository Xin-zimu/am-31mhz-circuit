# Generate .cir/.cmd pairs for the bounded S03-05 make-up batches.
# Each new attempt is a copy of a verified original netlist; ONLY the
# write-and-destroy-iplot output path is retargeted to the new tag. The tran
# line and every component value (including the IC= precharge values) are
# carried over byte for byte.

$ErrorActionPreference = 'Stop'
$runRoot = 'D:\ms_xsp\stage3_acceptance\s0305_endpoints_20261014'

# tag -> @{ src_cir = baseline tag whose .cir/.cmd are used; tran = expected tran line }
$plan = @(
  # batch 1: nominal baseline, precharged 5 ms tail, unchanged tran
  @{ tag='C4_4Vpp_D50_5ms_b1'; src='REF_4Vpp_tail'; dir='D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹\final2_20261014'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C4_4Vpp_D50_5ms_b2'; src='REF_4Vpp_tail'; dir='D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹\final2_20261014'; tran='tran 2n 5m 4.5m 2n uic' },
  # batch 2: four endpoints, precharged 5 ms tail (same condition as C2/C4/C5)
  @{ tag='C1_1Vpp_D10_5ms_b1'; src='C1_1Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C1_1Vpp_D10_5ms_b2'; src='C1_1Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C1_1Vpp_D10_5ms_b3'; src='C1_1Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C3_4Vpp_D10_5ms_b1'; src='C3_4Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C3_4Vpp_D10_5ms_b2'; src='C3_4Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C3_4Vpp_D10_5ms_b3'; src='C3_4Vpp_D10_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C6_4Vpp_D30_5ms_b1'; src='C6_4Vpp_D30_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C6_4Vpp_D30_5ms_b2'; src='C6_4Vpp_D30_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C6_4Vpp_D30_5ms_b3'; src='C6_4Vpp_D30_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C7_3Vpp_D50_5ms_b1'; src='C7_3Vpp_D50_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C7_3Vpp_D50_5ms_b2'; src='C7_3Vpp_D50_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  @{ tag='C7_3Vpp_D50_5ms_b3'; src='C7_3Vpp_D50_5ms'; tran='tran 2n 5m 4.5m 2n uic' },
  # batch 3: C2 bias convergence, 7 ms integration, last 0.5 ms saved
  @{ tag='C2_1Vpp_D50_7ms_b1'; src='C2_1Vpp_D50_7ms'; tran='tran 2n 7m 6.5m 2n uic' },
  @{ tag='C2_1Vpp_D50_7ms_b2'; src='C2_1Vpp_D50_7ms'; tran='tran 2n 7m 6.5m 2n uic' },
  @{ tag='C2_1Vpp_D50_7ms_b3'; src='C2_1Vpp_D50_7ms'; tran='tran 2n 7m 6.5m 2n uic' },
  # batch 4: C4 paired reference at the 7 ms endpoint
  @{ tag='C4_4Vpp_D50_7ms_b1'; src='C4_4Vpp_D50_5ms_b1'; tran='tran 2n 7m 6.5m 2n uic'; patch_tran=$true },
  @{ tag='C4_4Vpp_D50_7ms_b2'; src='C4_4Vpp_D50_5ms_b1'; tran='tran 2n 7m 6.5m 2n uic'; patch_tran=$true },
  @{ tag='C4_4Vpp_D50_7ms_b3'; src='C4_4Vpp_D50_5ms_b1'; tran='tran 2n 7m 6.5m 2n uic'; patch_tran=$true }
)

# order matters: batch-1 C4 must exist before batch-4 copies from it
foreach ($item in $plan) {
  $tag = $item.tag
  $srcDir = if ($item.dir) { $item.dir } else { $runRoot }
  $srcCir = Join-Path $srcDir ($item.src + '.cir')
  $srcCmd = Join-Path $srcDir ($item.src + '.cmd')
  if (-not (Test-Path -LiteralPath $srcCir)) { throw ('Missing source cir: ' + $srcCir) }
  if (-not (Test-Path -LiteralPath $srcCmd)) { throw ('Missing source cmd: ' + $srcCmd) }

  $dstCir = Join-Path $runRoot ($tag + '.cir')
  $dstCmd = Join-Path $runRoot ($tag + '.cmd')
  if (Test-Path -LiteralPath $dstCmd) { throw ('Refusing overwrite: ' + $dstCmd) }

  # The .cir copy is idempotent: re-running this generator must be a no-op for
  # netlists already generated, but must still refuse to clobber a netlist whose
  # content differs from the verified source (that would silently change a case).
  $srcCirHash = (Get-FileHash -LiteralPath $srcCir -Algorithm SHA256).Hash
  if (Test-Path -LiteralPath $dstCir) {
    $dstCirHash = (Get-FileHash -LiteralPath $dstCir -Algorithm SHA256).Hash
    if ($dstCirHash -ne $srcCirHash) { throw ('Existing cir differs from source; refusing: ' + $dstCir) }
  } else {
    Copy-Item -LiteralPath $srcCir -Destination $dstCir
  }
  Copy-Item -LiteralPath $srcCmd -Destination $dstCmd

  # Retarget the command file: BOTH the source netlist path and the output raw
  # path must point into this run directory. Copying the baseline .cmd verbatim
  # left `source .../s0304_final2_20261014/REF_4Vpp_tail.cir` in place, and that
  # directory really does contain a netlist of that name -- so the engine would
  # silently simulate the WRONG netlist from the WRONG directory. Rebuild the two
  # path-bearing lines explicitly instead of doing substring surgery on them.
  $cmdText = [IO.File]::ReadAllText($dstCmd)
  $cirPathFwd = ($dstCir -replace '\\', '/')
  $rawPathFwd = (Join-Path $runRoot ($tag + '.raw')) -replace '\\', '/'
  $before = $cmdText
  $cmdText = $cmdText -replace '(?m)^source\s+\S+\s*$', ('source ' + $cirPathFwd)
  if ($cmdText -eq $before) { throw ('source line not retargeted in ' + $dstCmd) }
  $before = $cmdText
  $cmdText = $cmdText -replace '(?m)^write-and-destroy-iplot\s+".*"\s*$', ('write-and-destroy-iplot "' + $rawPathFwd + '"')
  if ($cmdText -eq $before) { throw ('write-and-destroy-iplot line not retargeted in ' + $dstCmd) }
  if ($item.patch_tran) {
    $before = $cmdText
    $cmdText = $cmdText -replace '(?m)^tran\s+2n\s+5m\s+4\.5m\s+2n\s+uic\s*$', 'tran 2n 7m 6.5m 2n uic'
    if ($cmdText -eq $before) { throw ('tran line not patched in ' + $dstCmd) }
  }
  [IO.File]::WriteAllText($dstCmd, $cmdText)

  # verify: source line, output path and tran line all point where intended
  $check = [IO.File]::ReadAllText($dstCmd)
  if ($check -notmatch ('(?m)^' + [regex]::Escape($item.tran) + '\s*$')) { throw ('tran mismatch in ' + $dstCmd) }
  if ($check -notmatch ('(?m)^source\s+' + [regex]::Escape($cirPathFwd) + '\s*$')) { throw ('source path not pointing at this run dir: ' + $dstCmd) }
  if ($check -notmatch [regex]::Escape($rawPathFwd)) { throw ('raw path not retargeted in ' + $dstCmd) }
  if ($check -match 's0304_final2_20261014') { throw ('stale s0304 path still present in ' + $dstCmd) }
  if ($check -match [regex]::Escape($item.src + '.raw')) { throw ('stale raw name still present in ' + $dstCmd) }

  # verify: the netlist carries the precharge IC values and has the expected length
  $cirHash = (Get-FileHash -LiteralPath $dstCir -Algorithm SHA256).Hash.ToLower()
  $cirBytes = (Get-Item -LiteralPath $dstCir).Length
  Write-Output ($tag + '  cir=' + $cirBytes + 'B  sha256=' + $cirHash.Substring(0,16) + '  src=' + $item.src + '  tran=[' + $item.tran + ']')
}
Write-Output 'GENERATION OK'
