"""Check every number printed on a drawing against the stored JSON results.

A schematic that quotes a stale figure is as wrong as a mis-wired one, so the
tokens the sheets assert are compared with results/*.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'results'
SRC = Path(__file__).resolve().parent / 'draw_schematics.py'


def g(n):
    return json.loads((RES / f'{n}.json').read_text(encoding='utf8'))


def peak(j):
    v = j['y']
    return max(abs(v['min']), abs(v['max']))


# run -> (description, list of strings that must appear in the drawing source)
CHECKS = [
    ('A470_nom', 'candidate A', ['TP2 2.801', '0.954', '-12.13', '15.23', '0.073', '1.028']),
    ('SA_510_680', 'A recommended sizing', ['0.939']),
    ('SA_330_620', 'A closest sizing', ['1.989', '1.199', '0.987']),
    ('B_Z06_nom', 'candidate B', ['3.2455', '0.608', '0.687', '0.5998',
                                  '-24.16', '-1.34', '8.72', '26.334', '150.376']),
    ('C_B_nom', 'candidate C', ['2.199', '0.877', '0.872', '0.5935',
                                '-4.94', '-3.97', '18.81', '0.108']),
]

# values that must no longer appear anywhere in the drawing source
FORBIDDEN = ['5.73 %']
REQUIRED = ['-2.250 V (measured)']


def main():
    src = SRC.read_text(encoding='utf8')
    ok = True

    print('=== numbers quoted on the sheets vs results/*.json ===')
    for run, desc, tokens in CHECKS:
        j = g(run)
        print(f'\n  {run}  ({desc})')
        print(f'    json: TP2={j["out"]["vpp"]:.4f}  Ypp={j["y"]["vpp"]:.4f}  '
              f'Ypeak={peak(j):.4f}  Zpp={j["z"]["vpp"]:.4f}  '
              f'ratio={j["z_y_amplitude_ratio"]:.4f}  '
              f'phY={j["y_phase_relative_tp2_deg"]:.2f}  '
              f'phZ={j["z_phase_relative_y_deg"]:.3f}  '
              f'thd={j["y"]["thd"]*100:.2f}%  mW={j["supply_mw"]:.3f}')
        for tok in tokens:
            if tok in src:
                print(f'    ok      token {tok!r}')
            else:
                ok = False
                print(f'    MISSING token {tok!r}')

    print('\n=== stale values that must be gone ===')
    for bad in FORBIDDEN:
        if bad in src:
            ok = False
            print(f'    STALE: {bad!r} still present')
        else:
            print(f'    clear: {bad!r}')

    print('\n=== required warnings ===')
    for need in REQUIRED:
        if need in src:
            print(f'    ok      {need!r}')
        else:
            ok = False
            print(f'    MISSING {need!r}')

    print('\n=== baseband figures ===')
    bb = g('bb_prepost_a4_d10')
    perr = bb['plateau_max_error_v'] * 1000
    extra = bb['positive_extra_mw'] + bb['negative_extra_mw']
    print(f'    json: X plateau error = {perr:.4f} mV, extra = {extra:.3f} mW')
    for tok, label in (('0.180', 'X plateau 0.180 mV'), ('10.2', 'per-stage 10.2 mW')):
        if tok in src:
            print(f'    ok      {label}')
        else:
            ok = False
            print(f'    MISSING {label}')

    print('\nOVERALL:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
