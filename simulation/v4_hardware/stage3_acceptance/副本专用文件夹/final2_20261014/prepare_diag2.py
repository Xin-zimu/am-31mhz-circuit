"""Cheap, decisive diagnostics for the TSTOP ceiling question.

KEY OBSERVATION: the 12 ms tail failed after 74 s while a leftover GUI Multisim
instance (PID 24344, project S03_GUI_COLD_20us) was still open. After killing it,
the 20 ms diagnostic ran >4 min with no error before being interrupted.

So two hypotheses must be separated:
  H1  the solver rejects/aborts large TSTOP  -> a real ceiling near 9 ms
  H2  the leftover GUI instance interfered   -> 12 ms may be fine when clean

TEST 1 (fast, ~1 min): the trivial RC netlist L0_plain at TSTOP=20 ms.
  If a 3-element circuit also fails, the ceiling is global (H1).
  If it passes, the ceiling depends on the circuit, not on TSTOP alone.

TEST 2 (the real question, ~14 min): re-run the 12 ms tail with NO other
  Multisim instance alive.

Prepares inputs only.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
KEEP = HERE.parent
COLD = KEEP / 'engine/L_7ms_1ns.cir'
RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
RUNTIME.mkdir(parents=True, exist_ok=True)

# ---------------- TEST 1: trivial RC at 20 ms -------------------------
RC = b"""* TSTOP ceiling probe: trivial RC, no switches, no macromodels
V1 in 0 SIN(0 1 1k)
R1 in out 1k
C1 out 0 100n
.end
"""
RC_TAG = 'PROBE_rc_20ms'
rc_cmd = f'''source {RUNTIME.as_posix()}/{RC_TAG}.cir
begin-scope page Transient Analysis
save $out
iplot $out
tran 1u 20m 0 1u uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{RC_TAG}.raw"
end-scope
'''.encode('ascii')

# ---------------- TEST 2: clean 12 ms cold tail ------------------------
cold = COLD.read_bytes()
T12_TAG = 'COLD_12ms_clean'
t12_cmd = f'''source {RUNTIME.as_posix()}/{T12_TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 12m 11.5m 1n uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{T12_TAG}.raw"
end-scope
'''.encode('ascii')

for d in (HERE, RUNTIME):
    (d / f'{RC_TAG}.cir').write_bytes(RC)
    (d / f'{RC_TAG}.cmd').write_bytes(rc_cmd)
    (d / f'{T12_TAG}.cir').write_bytes(cold)
    (d / f'{T12_TAG}.cmd').write_bytes(t12_cmd)

meta = {
    'date': '2026-10-14',
    'runtime_dir': str(RUNTIME),
    'observation_that_motivated_this': (
        'COLD_12ms_tail failed after 74 s while a leftover GUI Multisim instance '
        '(PID 24344) was open. COLD_9ms_tail succeeded (646 s) in the same session. '
        'After killing PID 24344, DIAG_20ms_tail ran >4 min with no error before '
        'being interrupted. Environmental interference is therefore a live '
        'hypothesis and must be excluded before declaring a ceiling.'),
    'tests': {
        RC_TAG: {
            'tran': 'tran 1u 20m 0 1u uic',
            'netlist': 'trivial RC (V1/R1/C1), 3 elements, no switches',
            'purpose': 'if THIS fails too, the ceiling is global and TSTOP-keyed; '
                       'if it passes, the ceiling is circuit-dependent',
            'expect': 'points = 20,001; runtime well under a minute',
        },
        T12_TAG: {
            'tran': 'tran 1n 12m 11.5m 1n uic',
            'netlist': str(COLD),
            'source_sha256': hashlib.sha256(cold).hexdigest(),
            'purpose': 'the actual 12 ms tail re-run with a clean environment',
            'expect': '~14 min; 0.5e6 points saved (~65 MB)',
        },
    },
    'protocol': 'run with NO other Multisim process alive; kill leftovers first',
}
(HERE / 'diag2_manifest.json').write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

print(json.dumps(meta, ensure_ascii=False, indent=2))
print()
for d in (HERE, RUNTIME):
    for tag in (RC_TAG, T12_TAG):
        for ext in ('cir', 'cmd'):
            p = d / f'{tag}.{ext}'
            print(f'  {p.stat().st_size:>8d} B  {p}')
