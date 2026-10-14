"""Decisive cheap diagnostic: is the failure an UPFRONT check on TSTOP,
or does it happen after accumulating integration work?

Evidence so far:
    tran 1n  7m  0    1n uic  -> SUCCESS  (9.5 min, 7e6 pts integrated)
    tran 1n  9m  8.5m 1n uic  -> SUCCESS  (10.8 min, 9e6 pts integrated, 0.5e6 saved)
    tran 1n 10m  0    1n uic  -> FAIL after 120 s  ("Internal simulation error.")
    tran 1n 12m 11.5m 1n uic  -> FAIL after  74 s

The 9 ms tail and the 12 ms tail SAVE the same volume (0.5e6 points), so the
save size is NOT the trigger. The remaining question: does Multisim reject
large TSTOP immediately, or does it die partway?

TEST: tran 1n 20m 19.5m 1n uic  (same tiny save window, far larger TSTOP)
  - fails in ~1-2 min  => UPFRONT rejection keyed on TSTOP
  - runs for many min  => accumulates work, then dies
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
KEEP = HERE.parent
COLD = KEEP / 'engine/L_7ms_1ns.cir'
RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')

base = COLD.read_bytes()
TAG = 'DIAG_20ms_tail'
cmd = f'''source {RUNTIME.as_posix()}/{TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 20m 19.5m 1n uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{TAG}.raw"
end-scope
'''.encode('ascii')

for d in (HERE, RUNTIME):
    (d / f'{TAG}.cir').write_bytes(base)
    (d / f'{TAG}.cmd').write_bytes(cmd)

meta = {
    'tag': TAG,
    'tran': 'tran 1n 20m 19.5m 1n uic',
    'purpose': 'distinguish upfront TSTOP rejection from accumulated-work failure',
    'source_sha256': hashlib.sha256(base).hexdigest(),
    'interpretation': {
        'fails_in_1_to_2_min': 'UPFRONT rejection keyed on TSTOP -> 9 ms is a hard ceiling',
        'runs_many_minutes': 'accumulated-work failure -> ceiling is on integration extent',
    },
}
(HERE / 'diag_manifest.json').write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(meta, ensure_ascii=False, indent=2))
print()
for d in (HERE, RUNTIME):
    for ext in ('cir', 'cmd'):
        p = d / f'{TAG}.{ext}'
        print(f'  {p.stat().st_size:>8d} B  {p}')
