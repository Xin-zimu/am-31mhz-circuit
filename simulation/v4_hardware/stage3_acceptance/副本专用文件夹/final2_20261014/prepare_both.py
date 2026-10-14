"""Prepare both remaining runs, fully self-contained.

  A) 12 ms cold-start tail   : tran 1n 12m 11.5m 1n uic   (cold, zero IC)
  B) 2 Vpp precharged linear : tran 2n 5m 0 2n uic       (precharged, D=50)

Run B mirrors the accepted nominal_5ms run EXACTLY except the two attenuator
resistors, so the 4 Vpp vs 2 Vpp comparison is like-for-like on the same
accepted baseline (S03-03). Cold start is deliberately NOT mixed in: it would
confound settling with linearity.

Creates inputs only; starts nothing.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
KEEP = HERE.parent
STAGE = KEEP.parent                      # stage3_acceptance
COLD_SRC = KEEP / 'engine/L_7ms_1ns.cir'                 # zero-IC netlist
NOM_SRC = STAGE / 'nominal_full.cir'                     # precharged netlist

RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
RUNTIME.mkdir(parents=True, exist_ok=True)

# ---- case A: 12 ms cold-start tail -------------------------------------
cold = COLD_SRC.read_bytes()
A_TAG = 'COLD_12ms_tail'
A_TRAN = 'tran 1n 12m 11.5m 1n uic'
a_cmd = f'''source {RUNTIME.as_posix()}/{A_TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
{A_TRAN}
write-and-destroy-iplot "{RUNTIME.as_posix()}/{A_TAG}.raw"
end-scope
'''.encode('ascii')

# ---- case B: 2 Vpp precharged ------------------------------------------
nom = NOM_SRC.read_bytes()
B_TAG = 'LIN_2Vpp_pre'
B_TRAN = 'tran 2n 5m 0 2n uic'

# D=50% row of potentiometer_settings.csv:
#   4 Vpp baseline (accepted)  RVAT=15460.748119  RVAB=4539.251881
#   2 Vpp target               RVAT=10905.544559  RVAB=9094.455441
SWAPS = [(b'rRVAT', b'15460.748119', b'10905.544559'),
         (b'rRVAB', b'4539.251881', b'9094.455441')]
changes = []
for comp, old, new in SWAPS:
    pat = rb'(?m)^(' + comp + rb'\s+\S+\s+\S+\s+)(\S+)'
    m = re.search(pat, nom)
    if not m:
        raise SystemExit(f'{comp.decode()} not found in {NOM_SRC}')
    found = m.group(2)
    nom2, n = re.subn(pat, lambda mm: mm.group(1) + new, nom)
    if n != 1:
        raise SystemExit(f'{comp.decode()}: expected 1 replacement, got {n}')
    changes.append({'component': comp.decode(), 'old_ohm': found.decode(),
                    'new_ohm': new.decode()})

# receiver chain must be untouched (user requirement: keep receive gain fixed)
assert b'rRG_BB BB_FB VREF 10000' in nom2
assert b'rRF_BB BBO FB_TRIM 150000' in nom2
assert b'rRV_BB FB_TRIM BB_FB 3511' in nom2
assert b'rRLOAD V2 0 1000000' in nom2

b_cmd = f'''source {RUNTIME.as_posix()}/{B_TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
{B_TRAN}
write-and-destroy-iplot "{RUNTIME.as_posix()}/{B_TAG}.raw"
end-scope
'''.encode('ascii')

for d in (HERE, RUNTIME):
    for tag, net, cmd in [(A_TAG, cold, a_cmd), (B_TAG, nom2, b_cmd)]:
        (d / f'{tag}.cir').write_bytes(net)
        (d / f'{tag}.cmd').write_bytes(cmd)

# reference copy of the 4 Vpp baseline netlist for a same-method comparison
ref4 = nom
for d in (HERE, RUNTIME):
    (d / 'REF_4Vpp_pre.cir').write_bytes(ref4)
    (d / 'REF_4Vpp_pre.cmd').write_bytes(
        b_cmd.replace(B_TAG.encode(), b'REF_4Vpp_pre'))

manifest = {
    'date': '2026-10-14',
    'runtime_dir': str(RUNTIME),
    'cases': {
        A_TAG: {
            'tran': A_TRAN,
            'purpose': 'cold-start bias settling beyond 9 ms; report only 11.5-12.0 ms',
            'source': str(COLD_SRC),
            'source_sha256': hashlib.sha256(cold).hexdigest(),
            'changes': [],
            'initial': 'UIC zero (C111/C115/CBB = 0)',
            'expected_saving': '0.5 ms at 1 ns => ~0.5e6 points => ~65 MB',
            'why_12ms_is_safer_than_the_old_10ms': (
                'The archived 10 ms attempt emitted "Internal simulation error." after '
                'only ~2 min while trying to SAVE 10e6 points (~1.3 GB); the 9 ms tail '
                'run integrated 9e6 points in 10.8 min while saving only 0.5e6. '
                'Hypothesis: that failure was a save/memory limit, not an integration '
                'limit. TSTART caps the save volume, so 12 ms should be attempted.'),
        },
        B_TAG: {
            'tran': B_TRAN,
            'purpose': '2 Vpp linearity at D=50%, precharged, against the accepted 4 Vpp nominal',
            'source': str(NOM_SRC),
            'source_sha256': hashlib.sha256(nom).hexdigest(),
            'changes': changes,
            'initial': 'precharged (C111=0.43 V, C115=-4.1 V, CBB=4.5 V) as accepted in S03-03',
            'receiver_chain': 'untouched (RG_BB/RF_BB/RV_BB/RLOAD asserted present)',
        },
        'REF_4Vpp_pre': {
            'tran': B_TRAN,
            'purpose': 're-run of the accepted 4 Vpp baseline under identical options, '
                       'so the step-size difference (2 ns here vs 1.008 ns effective) '
                       'is visible and the comparison is same-method',
            'source': str(NOM_SRC),
            'source_sha256': hashlib.sha256(nom).hexdigest(),
            'changes': [],
        },
    },
    'entry': 'COM DoCommandLine; source + tran command engine. No native GUI pass claimed.',
    'acceptance_note': (
        'The 4 Vpp reference for the linearity comparison is the accepted S03-03 '
        'nominal (V2 robust 4.816023 Vpp, time-weighted mean 4.496041 V, output '
        '19,998.043 Hz, duty 50.22635% from the 2 ms GUI run).'),
}
(HERE / 'run_manifest.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

print(json.dumps(manifest, ensure_ascii=False, indent=2))
print()
print('created:')
for d in (HERE, RUNTIME):
    for p in sorted(d.glob('*.cir')) + sorted(d.glob('*.cmd')):
        print(f'  {p.stat().st_size:>8d} B  {p}')
