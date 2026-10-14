"""Read-only: (a) what changes character at 7 carrier periods; (b) how do the
three entry points differ in the archived evidence?  No simulator calls.
"""
from pathlib import Path
import sys
import json
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
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

print('=' * 98)
print('A. WHAT CHANGES AT 7 CARRIER PERIODS -- slope (dV/dt) per node')
print('=' * 98)
print('  If the circuit enters a new regime, the mean slope before/after differs.')
print()
print(f'  {"node":>10s} {"mean |dV/dt| 0-225 ns":>24s} {"226-500 ns":>16s} {"ratio":>10s}')
for i, lab in enumerate(labels, start=1):
    col = v[:, i]
    b = (t > 1e-9) & (t < EVENT - 1e-9)
    a = (t > EVENT + 1e-9) & (t < 500e-9)
    sb = np.abs(np.diff(col[b]) / np.diff(t[b])).mean()
    sa = np.abs(np.diff(col[a]) / np.diff(t[a])).mean()
    print(f'  {lab:>10s} {sb:24.6e} {sa:16.6e} {sa/sb if sb else float("nan"):10.4f}')

print()
print('  Ripple/slope detail across the boundary (engine samples):')
print(f'  {"t (ns)":>11s} {"dt (ps)":>9s} ' + ' '.join(f'{l:>13s}' for l in labels))
for k in np.flatnonzero((t > EVENT - 3e-9) & (t < EVENT + 8e-9)):
    print(f'  {t[k]*1e9:11.5f} {(t[k]-t[k-1])*1e12:9.3f} ' +
          ' '.join(f'{v[k, i+1]:13.8f}' for i in range(4)))

print()
print('=' * 98)
print('B. THE 31 MHz CARRIER RIPPLE -- is 7 periods when it reaches full swing?')
print('=' * 98)
print('  V(bbo) carries the demodulated/carrier-related ripple. Peak-to-peak per')
print('  carrier period, engine:')
print(f'  {"period k":>9s} {"t (ns)":>10s} {"V(bbo) pp":>12s} {"V(bb_in) pp":>13s} '
      f'{"V(v1) pp":>12s}')
for k in range(1, 16):
    lo, hi = (k - 1) * PERIOD, k * PERIOD
    m = (t >= lo) & (t < hi)
    if m.sum() < 3:
        continue
    print(f'  {k:9d} {hi*1e9:10.3f} {np.ptp(v[m, 2]):12.3e} {np.ptp(v[m, 1]):13.3e} '
          f'{np.ptp(v[m, 3]):12.3e}')

print()
print('=' * 98)
print('C. ENTRY POINTS -- what each actually is, and what it did')
print('=' * 98)
entries = [
    ('Native GUI',
     'Analyses and Simulation > Transient Analysis > Run',
     'full .tran analysis using the dialog TSTEP/TSTOP/TSTART/TMAX and its own solver options',
     'DIES at 225.80 ns (4 archived runs, 2 methods, 2 step caps)'),
    ('COM interactive',
     'MultisimInterface MultisimApp.OpenFile + Circuit.RunSimulation(chunk, true)',
     'interactive simulator driven in 100 ns chunks; not the .tran dialog path',
     'passed 20 us in the TMAX/TSTEP matrix (matrix3)'),
    ('COM batch / engine',
     'Circuit.DoCommandLine(source <cir> + tran ...)',
     'the SPICE command engine reading an explicit .tran card',
     'passed 20 us, 2 ms, 5 ms, 7 ms'),
]
for nm, api, desc, outcome in entries:
    print(f'  {nm}')
    print(f'    API     : {api}')
    print(f'    Meaning : {desc}')
    print(f'    Outcome : {outcome}')
    print()

print('  IMPORTANT: the 1 ns "fix" was validated on the COM interactive path')
print('  (matrix3 REACHED-TSTOP) and on the command engine (2/5/7 ms). The native')
print('  GUI was then run at 1/1 ns and STILL died at 225.797635 ns.')
print('  => the fix does not transfer to the GUI analysis path.')

(OUT / 'regime_and_entries.json').write_text(json.dumps({
    'event_s': EVENT, 'period_s': PERIOD, 'entries': [e[0] for e in entries],
}, ensure_ascii=False, indent=2), encoding='utf-8')
