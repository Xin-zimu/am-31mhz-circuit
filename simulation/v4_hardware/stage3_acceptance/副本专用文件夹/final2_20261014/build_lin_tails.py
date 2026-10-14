"""Switch the 2 Vpp linearity runs to TSTART tails.

Rationale:
  - Same integration from t=0 either way, so the last five cycles are unchanged.
  - TSTART was proven BIT-IDENTICAL to the full run in the overlap window
    (engine_acceptance_20261014/compare_tstart.py), including the step floor.
  - Saving 4.5-5.0 ms instead of 0-5 ms cuts the .raw from ~630 MB to ~63 MB,
    which removes the memory risk that plausibly killed the old 10 ms attempt.

Also drops the `set` lines: the command engine provably ignores .options, and
the accepted S03-03 nominal ran with them, so removing them cannot change the
result -- but keeping them is harmless too, so they are retained to stay
byte-close to the accepted baseline's command file.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')

TAG2 = 'LIN_2Vpp_tail'
TAG4 = 'REF_4Vpp_tail'
TRAN = 'tran 2n 5m 4.5m 2n uic'


def cmd_for(tag):
    return f'''source {RUNTIME.as_posix()}/{tag}.cir
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
{TRAN}
write-and-destroy-iplot "{RUNTIME.as_posix()}/{tag}.raw"
end-scope
'''.encode('ascii')


src2 = (HERE / 'LIN_2Vpp_pre.cir').read_bytes()
src4 = (HERE / 'REF_4Vpp_pre.cir').read_bytes()

for d in (HERE, RUNTIME):
    (d / f'{TAG2}.cir').write_bytes(src2)
    (d / f'{TAG2}.cmd').write_bytes(cmd_for(TAG2))
    (d / f'{TAG4}.cir').write_bytes(src4)
    (d / f'{TAG4}.cmd').write_bytes(cmd_for(TAG4))

meta = {
    'date': '2026-10-14',
    'runtime_dir': str(RUNTIME),
    'tran': TRAN,
    'why_tail': 'same integration from t=0; TSTART only limits what is SAVED; '
                'proven bit-identical in the overlap window',
    'expected_raw_MB': 63,
    'expected_minutes': 10,
    'cases': {
        TAG2: {'role': '2 Vpp measurement (D=50%)',
               'cir_sha256': hashlib.sha256(src2).hexdigest(),
               'att': {'rRVAT': '10905.544559', 'rRVAB': '9094.455441'},
               'initial': 'precharged'},
        TAG4: {'role': '4 Vpp reference under identical options',
               'cir_sha256': hashlib.sha256(src4).hexdigest(),
               'att': {'rRVAT': '1847.93', 'rRVAB': '18152.1'},
               'initial': 'precharged'},
    },
    'comparison_baseline': {
        'accepted_S03_03_nominal_V2_robust_vpp': 4.816022800305442,
        'accepted_S03_03_nominal_V2_mean_v': 4.496040582487098,
        'output_freq_hz': 19998.043,
        'duty_percent': 50.22635,
    },
}
(HERE / 'lin_tail_manifest.json').write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(meta, ensure_ascii=False, indent=2))
print()
for d in (HERE, RUNTIME):
    for tag in (TAG2, TAG4):
        for ext in ('cir', 'cmd'):
            p = d / f'{tag}.{ext}'
            print(f'  {p.stat().st_size:>8d} B  {p}')
