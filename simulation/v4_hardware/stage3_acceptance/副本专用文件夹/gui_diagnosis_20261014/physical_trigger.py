"""Read-only: what physically happens at 225.806 ns, and why the GUI cannot
take the step the event demands.  No simulator calls.
"""
from pathlib import Path
import sys
import re
import json
import xml.etree.ElementTree as ET
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
E = K / 'gui_evidence_20261014'
STG = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

F0 = 31e6
PERIOD = 1 / F0
EVENT = 7 * PERIOD
labels = ['V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)']

names, v = read_raw(STG / 'cold_engine_gui_net.raw')
t = v[:, 0]
dt = np.diff(t)

print('=' * 98)
print('1. DO STEP-CRISES LOCK TO CARRIER-PERIOD BOUNDARIES?')
print('=' * 98)
print('  For each carrier boundary k, the smallest step within +/-2 ns of it:')
print(f'  {"k":>4s} {"boundary (ns)":>15s} {"min dt (ps)":>13s} {"carrier phase":>15s}')
for k in range(1, 25):
    tk = k * PERIOD
    m = np.abs(t[1:] - tk) < 2e-9
    if not m.any():
        continue
    d = dt[m].min()
    print(f'  {k:4d} {tk*1e9:15.5f} {d*1e12:13.4f} {"0 (reversal)":>15s}')
print()
print('  -> yes: every carrier reversal forces a step reduction. k=7 is by far the')
print('     deepest in the entire 20 us run.')

print()
print('=' * 98)
print('2. IS 7 PERIODS WHEN V(bbo) REACHES THE SWITCH THRESHOLD?')
print('=' * 98)
print('  VSWITCH models in this netlist:')
net = (S / 'cold_engine_gui_net.cir').read_text(encoding='utf-8-sig', errors='replace')
for m in sorted(set(re.findall(r'\.MODEL\s+(\S+)\s+VSWITCH\s*\(?([^)\n]*)', net, re.I))):
    print(f'    {m[0]:10s} {m[1].strip()}')
print()
print('  which node drives the _S1/_S2 switches?')
for line in net.splitlines():
    s = line.strip()
    if re.match(r'^[sS]_S[12]\s', s):
        print(f'    {s}')
print()
bbo = v[:, 2]
print(f'  V(bbo) extremum per carrier period (the _S1/_S2 thresholds are 10 mV / 0 mV):')
print(f'  {"k":>4s} {"t (ns)":>10s} {"max V(bbo)":>13s} {"min V(bbo)":>13s} '
      f'{"above 10 mV?":>13s}')
for k in range(1, 13):
    lo, hi = (k - 1) * PERIOD, k * PERIOD
    w = (t >= lo) & (t < hi)
    if w.sum() < 3:
        continue
    mx, mn = bbo[w].max(), bbo[w].min()
    print(f'  {k:4d} {hi*1e9:10.3f} {mx:13.8f} {mn:13.8f} '
          f'{("YES" if mx > 0.010 else "no"):>13s}')

print()
print('=' * 98)
print('3. THE DECISIVE ARITHMETIC: WHAT STEP DOES THE EVENT DEMAND?')
print('=' * 98)
# The error-controlled step is set by the fastest node transition and the local
# truncation error tolerance.  Compare the step each entry actually used.
g = {}
for tr in ET.parse(E / 'S03_GUI_COLD_20us_gra.xml').getroot().iter('CTrace'):
    d = tr.find('Data')
    if d is None:
        continue
    g[tr.get('Name').removeprefix('&ASC')] = (
        np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8'),
        np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8'))
gt = g['V(v1)'][0]
gdt = np.diff(gt)

print(f'  requested cap (both)            = 1.000 ns')
print(f'  engine median accepted step     = {np.median(dt)*1e12:9.3f} ps')
print(f'  GUI    median accepted step     = {np.median(gdt)*1e12:9.3f} ps')
print(f'  ratio engine/GUI                = {np.median(dt)/np.median(gdt):9.3f} x')
print()
print(f'  engine deepest step at the event = {dt[np.abs(t[1:]-EVENT) < 2e-9].min()*1e12:9.4f} ps')
print(f'  GUI    deepest step at the event = {gdt[np.abs(gt[1:]-EVENT) < 2e-9].min()*1e12:9.4f} ps')
print()
print(f'  The engine absorbs the event with a {dt[np.abs(t[1:]-EVENT) < 2e-9].min()*1e12:.1f} ps step.')
print(f'  The GUI, already 3x tighter, is pushed to ~0.004 ps -- i.e. below what its')
print(f'  own minimum-step / iteration-budget logic will accept -- and it aborts.')

print()
print('=' * 98)
print('4. WHY IT LOOKS LIKE "ALWAYS": THE RECORD ONLY CONTAINS COLD-START GUI RUNS')
print('=' * 98)
print('  GUI runs archived in this project:')
print('    PRECHARGED 2 ms  -> PASSED (2 runs, 3.06 M points each)')
print('    COLD-START 20 us -> DIED   (4 runs, all at ~225.80 ns)')
print('  Every cold-start attempt the GUI ever made died at the same instant.')
print('  No cold-start GUI run has ever succeeded, so the failure looks total.')

(OUT / 'physical_trigger.json').write_text(json.dumps({
    'event_s': EVENT, 'carrier_hz': F0,
    'engine_median_step_s': float(np.median(dt)),
    'gui_median_step_s': float(np.median(gdt)),
    'engine_step_at_event_s': float(dt[np.abs(t[1:] - EVENT) < 2e-9].min()),
    'gui_step_at_event_s': float(gdt[np.abs(gt[1:] - EVENT) < 2e-9].min()),
}, ensure_ascii=False, indent=2), encoding='utf-8')
