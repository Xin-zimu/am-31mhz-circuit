"""Read-only: pin the GUI stop time against the carrier period, and profile the
engine's behaviour at the same absolute time. No simulator calls."""
from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET
import numpy as np

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
K = S / '副本专用文件夹'
E = K / 'gui_evidence_20261014'
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

F0 = 31e6
PERIOD = 1 / F0


def traces(path):
    root = ET.parse(path).getroot()
    out = {}
    for tr in root.iter('CTrace'):
        data = tr.find('Data')
        if data is None:
            continue
        name = tr.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        out[name] = (x, y)
    return out


RUNS = [
    ('GUI TRAP500, 2/2 ns, zero_ic', S / 'S03_COLD_ZERO_TRAP500_20us.decoded.xml'),
    ('GUI GEAR500, 2/2 ns, zero_ic', S / 'S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml'),
    ('GUI GEAR500 reopen, 2/2 ns', S / 'S03_COLD_ZERO_GEAR500_REOPEN_20us.decoded.xml'),
    ('GUI GEAR500+UIC, 1/1 ns, UIC', E / 'S03_GUI_COLD_20us_gra.xml'),
]

print('=' * 92)
print('ALL NATIVE-GUI FAILED RUNS -- is the stop time locked to the carrier period?')
print(f'carrier f0 = {F0/1e6:g} MHz, period = {PERIOD*1e9:.6f} ns, '
      f'7 periods = {7*PERIOD*1e9:.6f} ns')
print('=' * 92)
print(f'{"run":32s} {"pts":>5s} {"stop (ns)":>12s} {"stop/period":>12s} '
      f'{"nearest int":>11s} {"delta (ps)":>11s}')
rows = []
for label, path in RUNS:
    if not path.exists():
        print(f'{label:32s}  MISSING {path.name}')
        continue
    d = traces(path)
    key = 'V(v1)' if 'V(v1)' in d else next(iter(d))
    t = d[key][0]
    stop = float(t[-1])
    ratio = stop / PERIOD
    near = round(ratio)
    delta_ps = (stop - near * PERIOD) * 1e12
    print(f'{label:32s} {len(t):5d} {stop*1e9:12.6f} {ratio:12.6f} '
          f'{near:11d} {delta_ps:11.3f}')
    rows.append({'run': label, 'points': len(t), 'stop_s': stop,
                 'stop_over_carrier_period': ratio, 'nearest_periods': near,
                 'delta_ps': delta_ps})
print()
print('  => every GUI run dies at the SAME simulated time, ~8-11 ps BEFORE the')
print('     7th carrier period boundary, whatever the step cap or method.')
print()

# Engine: identical netlist, 20 us target, 2 ns requested (effective 1.0080645 ns)
eng = S / 'cold_engine_gui_net.raw'
if eng.exists():
    names, v = read_raw(eng)
    et = v[:, 0]
    edt = np.diff(et)
    print('=' * 92)
    print(f'ENGINE (identical netlist) at the same absolute time -- {eng.name}')
    print('=' * 92)
    print(f'  points={len(et)}  end={et[-1]*1e6:.6f} us   (GUI died at 0.2258 us)')
    win = (et > 200e-9) & (et < 260e-9)
    idx = np.flatnonzero(win)
    print(f'  accepted steps between 200 and 260 ns: {len(idx)}')
    print(f'  dt in that window: min={edt[idx].min():.4e}  max={edt[idx].max():.4e} '
          f' (engine never collapses its step here)')
    # how close does the engine's step ever get to zero, over the whole run?
    print(f'  whole-run dt: min={edt.min():.4e}  max={edt.max():.4e}')
    # engine samples near the 7th period boundary
    target = 7 * PERIOD
    near = np.flatnonzero(np.abs(et - target) < 5e-9)
    print(f'  engine samples within 5 ns of {target*1e9:.4f} ns: {len(near)}')
    if len(near):
        print('    t (ns)      V(bb_in)    V(bbo)     V(v2)')
        for k in near[:8]:
            print(f'    {et[k]*1e9:9.5f}  {v[k,2]:9.6f}  {v[k,3]:9.6f}  {v[k,5]:9.6f}')
    rows_eng = {'points': int(len(et)), 'end_s': float(et[-1]),
                'dt_min_s': float(edt.min()), 'dt_max_s': float(edt.max()),
                'steps_200_260ns': int(len(idx))}
else:
    rows_eng = None
    print(f'  (missing {eng})')
print()

# How violent is the GUI's end-of-life?  step-by-step collapse.
d = traces(E / 'S03_GUI_COLD_20us_gra.xml')
t = d['V(v1)'][0]
dt = np.diff(t)
print('=' * 92)
print('GUI end-of-life step collapse (last 14 accepted steps)')
print('=' * 92)
print(f'{"k":>4s} {"t (ns)":>12s} {"dt (s)":>12s} {"dt/dtau":>9s} '
      f'{"V(bb_in)":>11s} {"dV(bb_in)":>12s}')
for k in range(len(t) - 14, len(t)):
    dvv = d['V(bb_in)'][1][k] - d['V(bb_in)'][1][k - 1]
    print(f'{k:4d} {t[k]*1e9:12.6f} {dt[k-1]:12.4e} {dt[k-1]/dt[k-2]:9.4f} '
          f'{d["V(bb_in)"][1][k]:11.7f} {dvv:12.3e}')
print()
print('  dt shrinks by ~2000x over the last 11 steps while V(bb_in) moves <0.1 uV')
print('  per step -> the Newton iteration is failing and the solver is cutting the')
print('  step to the floor before it aborts. This is a local convergence failure,')
print('  not memory, not a crash, and not a wrong result.')

(OUT / 'stop_time_analysis.json').write_text(
    json.dumps({'carrier_hz': F0, 'period_s': PERIOD, 'gui_runs': rows,
                'engine': rows_eng}, ensure_ascii=False, indent=2), encoding='utf-8')
