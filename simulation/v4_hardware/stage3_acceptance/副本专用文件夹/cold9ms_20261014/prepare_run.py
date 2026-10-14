"""Prepare the isolated 9 ms cold-start tail run (tran 1n 9m 8.5m 1n uic).

Mirrors engine_acceptance_20261014/prepare_runs.py but writes to a dedicated
9 ms folder so nothing existing is touched. Creates inputs only; runs nothing.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'engine/L_7ms_1ns.cir'      # proven 7 ms source netlist
RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014')
RUNTIME.mkdir(parents=True, exist_ok=True)

base = SRC.read_bytes()
TAG = 'COLD_9ms_tail'
cmd = f'''source {RUNTIME.as_posix()}/{TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 9m 8.5m 1n uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{TAG}.raw"
end-scope
'''.encode('ascii')

netlist_sha = hashlib.sha256(base).hexdigest()
cmd_sha = hashlib.sha256(cmd).hexdigest()

for directory in [HERE, RUNTIME]:
    with (directory / f'{TAG}.cir').open('xb') as f:
        f.write(base)
    with (directory / f'{TAG}.cmd').open('xb') as f:
        f.write(cmd)

manifest = {
    'date': '2026-10-14',
    'tag': TAG,
    'purpose': 'cold-start settling beyond the 7 ms window; report only 8.5-9.0 ms',
    'tran': 'tran 1n 9m 8.5m 1n uic',
    'tstart_s': 8.5e-3, 'tstop_s': 9e-3, 'tstep_s': 1e-9, 'tmax_s': 1e-9,
    'tstart_validated_by': 'engine_acceptance_20261014/compare_tstart.py '
                           '(bit-identical overlap vs full-window run)',
    'source': str(SRC),
    'source_sha256': netlist_sha,
    'command_sha256': cmd_sha,
    'entry': 'COM DoCommandLine; source + tran command engine. No native GUI pass claimed.',
    'runtime_dir': str(RUNTIME),
    'risk': '9 ms unverified: 7 ms succeeded, 10 ms previously reported '
            '"Internal simulation error". If 9 ms fails, fall back to the longest '
            'verified window (7 ms) and record the drift rather than changing criteria.',
}
(HERE / 'run_manifest.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
print()
print('created:')
for directory in [HERE, RUNTIME]:
    for ext in ['cir', 'cmd']:
        p = directory / f'{TAG}.{ext}'
        print(f'  {p.stat().st_size:>8d} B  {p}')
