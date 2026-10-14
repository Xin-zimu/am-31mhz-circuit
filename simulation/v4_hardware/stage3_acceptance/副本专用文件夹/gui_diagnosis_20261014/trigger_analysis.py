"""Read-only: what is special about 225.806 ns?  Which node state changes?

No simulator calls.
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

names, v = read_raw(STG / 'cold_engine_gui_net.raw')
t = v[:, 0]
labels = ['V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)']

print('=' * 96)
print('1. THE ENGINE AROUND THE EVENT -- which node forces the step down?')
print('=' * 96)
w = np.flatnonzero((t > EVENT - 6e-9) & (t < EVENT + 6e-9))
print(f'  event = {EVENT*1e9:.6f} ns   (carrier phase 0, maximum slope)')
print()
print(f'  {"t (ns)":>11s} {"dt (ps)":>9s} ' + ' '.join(f'{l:>12s}' for l in labels))
for k in w:
    dtp = (t[k] - t[k-1]) * 1e12
    print(f'  {t[k]*1e9:11.5f} {dtp:9.3f} ' +
          ' '.join(f'{v[k, i+1]:12.7f}' for i in range(4)))

print()
print('  per-node |dV| across the deepest 3 steps vs the typical step:')
deep = np.flatnonzero((t > EVENT - 1e-9) & (t < EVENT + 2e-9))
for i, lab in enumerate(labels, start=1):
    col = v[:, i]
    if len(deep) >= 4:
        d_deep = np.abs(np.diff(col[deep[:4]]))
        # typical: median |dV| per step over the whole run
        d_all = np.abs(np.diff(col))
        print(f'    {lab:10s} deepest-step |dV| max = {d_deep.max():.3e} V   '
              f'run median |dV| = {np.median(d_all):.3e} V   '
              f'ratio = {d_deep.max()/np.median(d_all):9.2f}')

print()
print('=' * 96)
print('2. IS THE EVENT PERIODIC OR ONE-OFF?')
print('=' * 96)
dt = np.diff(t)
print(f'  every carrier-period boundary up to 1 us, and the smallest step within')
print(f'  +/- 2 ns of it (engine, 20 us run):')
print(f'  {"k-th period":>12s} {"t (ns)":>11s} {"min dt (ps)":>12s} {"steps<50ps":>10s}')
for k in range(1, 32):
    tk = k * PERIOD
    m = np.abs(t[1:] - tk) < 2e-9
    if not m.any():
        continue
    d = dt[m]
    print(f'  {k:12d} {tk*1e9:11.5f} {d.min()*1e12:12.4f} {int((d < 50e-12).sum()):10d}')

print()
print('=' * 96)
print('3. SANITY: THE CEILING RULE min(requested, period/32)')
print('=' * 96)
for label, path, req in [('engine 2 ns request', STG / 's0304/M_2n_2n.raw', 2e-9),
                         ('engine 1 ns request', STG / 's0304/Z_2ms_1ns.raw', 1e-9),
                         ('engine 500 ps request', STG / 's0304/W_tmax500p_20u.raw', 500e-12),
                         ('engine 100 ps request', STG / 's0304/W_tmax100p_20u.raw', 100e-12)]:
    if not path.exists():
        continue
    _, vv = read_raw(path)
    tt = vv[:, 0]
    d = np.diff(tt)
    pred = min(req, PERIOD / 32)
    print(f'  {label:24s} requested={req*1e12:8.1f} ps  observed max dt='
          f'{d.max()*1e12:9.3f} ps  predicted={pred*1e12:9.3f} ps  '
          f'match={abs(d.max()-pred) < 1e-18 or abs(d.max()/pred - 1) < 1e-6}')

(OUT / 'trigger_analysis.json').write_text(json.dumps({
    'event_s': EVENT, 'period_s': PERIOD,
    'ceiling_rule': 'effective TMAX = min(requested TMAX, carrier_period/32)',
}, ensure_ascii=False, indent=2), encoding='utf-8')
