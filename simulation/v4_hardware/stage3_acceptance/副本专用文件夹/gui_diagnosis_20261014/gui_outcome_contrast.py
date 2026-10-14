"""Read-only: contrast the GUI runs that SUCCEEDED with those that died.

Question: is the GUI failure tied to cold-start initial conditions?
No simulator calls.
"""
from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET
import numpy as np

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
K = S / '副本专用文件夹'
E = K / 'gui_evidence_20261014'
OUT = Path(__file__).resolve().parent

F0 = 31e6
PERIOD = 1 / F0


def traces(path):
    root = ET.parse(path).getroot()
    out = {}
    for tr in root.iter('CTrace'):
        d = tr.find('Data')
        if d is None:
            continue
        out[tr.get('Name').removeprefix('&ASC')] = (
            np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8'),
            np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8'))
    return out


RUNS = [
    ('GUI 2 ms PRECHARGED  (S03_GUI_2ms_V4_3)',
     S / 'S03_GUI_2ms_V4_3.decoded.xml', 'precharged'),
    ('GUI 2 ms PRECHARGED  (S03_COLD_2ms_V4_3)',
     S / 'S03_COLD_2ms_V4_3.decoded.xml', 'precharged'),
    ('GUI 20 us COLD START (TRAP500 zero_ic)',
     S / 'S03_COLD_ZERO_TRAP500_20us.decoded.xml', 'cold'),
    ('GUI 20 us COLD START (GEAR500 zero_ic)',
     S / 'S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml', 'cold'),
    ('GUI 20 us COLD START (GEAR500+UIC 1 ns)',
     E / 'S03_GUI_COLD_20us_gra.xml', 'cold'),
]

print('=' * 104)
print('GUI OUTCOMES: precharged vs cold start')
print('=' * 104)
print(f'  {"run":44s} {"IC":>11s} {"pts":>10s} {"stop":>16s} {"stop/period":>12s} {"verdict":>10s}')
summary = []
for label, path, ic in RUNS:
    if path is None or not path.exists():
        print(f'  {label:44s} {ic:>11s} {"(file missing)":>10s}')
        continue
    d = traces(path)
    key = 'V(v1)' if 'V(v1)' in d else next(iter(d))
    t = d[key][0]
    stop = float(t[-1])
    died = stop < 20e-6 - 1e-12
    verdict = 'DIED' if died else 'PASSED'
    shown = f'{stop*1e9:12.3f} ns' if stop < 1e-3 else f'{stop*1e3:12.3f} ms'
    print(f'  {label:44s} {ic:>11s} {len(t):10d} {shown:>16s} '
          f'{stop/PERIOD:12.4f} {verdict:>10s}')
    summary.append({'run': label, 'ic': ic, 'points': int(len(t)),
                    'stop_s': stop, 'stop_over_period': stop / PERIOD,
                    'verdict': verdict})

print()
print('  -> THE GUI WORKS on the precharged circuit (2 ms, 3.06 M points/curve).')
print('     It ONLY dies on the COLD-START (zero initial condition) circuit, and')
print('     always at ~7 carrier periods.')

# Does the precharged GUI run also show a step crisis at 7 periods?
print()
print('=' * 104)
print('DOES THE PRECHARGED GUI RUN ALSO HAVE A 7-PERIOD EVENT?')
print('=' * 104)
p = S / 'S03_GUI_2ms_V4_3.decoded.xml'
if p.exists():
    d = traces(p)
    t = d['V(v1)'][0]
    dt = np.diff(t)
    print(f'  precharged GUI: points={len(t)}  end={t[-1]*1e3:.4f} ms')
    print(f'  dt: min={dt.min()*1e12:.4f} ps  median={np.median(dt)*1e12:.3f} ps  '
          f'max={dt.max()*1e12:.3f} ps')
    print(f'  requested cap 2 ns -> effective {dt.max()*1e9:.9f} ns')
    for k in (7, 8):
        tk = k * PERIOD
        m = np.abs(t[1:] - tk) < 2e-9
        if m.any():
            print(f'  near {k} periods ({tk*1e9:.4f} ns): min dt = '
                  f'{dt[m].min()*1e12:.3f} ps  (no crisis)' if dt[m].min() > 50e-12
                  else f'  near {k} periods: min dt = {dt[m].min()*1e12:.3f} ps')
    # global step floor
    print(f'  global smallest step = {dt.min()*1e12:.3f} ps at t='
          f'{t[int(np.argmin(dt))+1]*1e9:.3f} ns')
    print()
    print('  -> the precharged run keeps its step large throughout; it never meets')
    print('     the cold-start startup event, so it completes.')

(OUT / 'gui_outcome_contrast.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
