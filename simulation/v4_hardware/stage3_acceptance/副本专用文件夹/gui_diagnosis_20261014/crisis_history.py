"""Read-only: characterise the step-size crises over time in the engine runs.

Question: is ~225.8 ns a special instant, or just the first crisis the
project-solver path cannot survive? No simulator calls.
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
CAP = 1.0080645161290323e-9
GUI_STOP = 225.797635e-9


def crises(t, dt, thresh):
    """Group consecutive samples with dt < thresh into events; report the deepest."""
    idx = np.flatnonzero(dt < thresh)
    events = []
    if not len(idx):
        return events
    start = idx[0]
    prev = idx[0]
    for k in idx[1:]:
        if k != prev + 1:
            seg = slice(start, prev + 1)
            j = start + int(np.argmin(dt[seg]))
            events.append((float(t[j]), float(dt[j]), prev - start + 1))
            start = k
        prev = k
    seg = slice(start, prev + 1)
    j = start + int(np.argmin(dt[seg]))
    events.append((float(t[j]), float(dt[j]), prev - start + 1))
    return events


RUNS = [
    ('engine 20 us (same netlist as the GUI failure)',
     STG / 'cold_engine_gui_net.raw', 20e-6),
    ('engine 20 us, TSTEP=TMAX=2 ns request (M_2n_2n)',
     STG / 's0304/M_2n_2n.raw', 2e-6),
    ('engine 2 ms, 1 ns (Z_2ms_1ns)',
     STG / 's0304/Z_2ms_1ns.raw', 2e-3),
    ('engine 7 ms cold start (L_7ms_1ns)',
     STG / 's0304/L_7ms_1ns.raw', 7e-3),
]

summary = {}
for label, path, span in RUNS:
    if not path.exists():
        print(f'--- {label}: MISSING {path}')
        continue
    names, v = read_raw(path)
    t = v[:, 0]
    dt = np.diff(t)
    print('=' * 92)
    print(f'{label}')
    print(f'  file={path.name}  points={len(t)}  end={t[-1]*1e6:.4f} us')
    print(f'  dt: min={dt.min()*1e12:.4f} ps  median={np.median(dt)*1e12:.2f} ps  '
          f'max={dt.max()*1e12:.2f} ps')
    n_cap = int((dt > 0.999 * CAP).sum())
    print(f'  steps at the {CAP*1e9:.6f} ns ceiling: {n_cap} / {len(dt)} '
          f'({100*n_cap/len(dt):.1f}%)')

    for thresh_ps in (50, 10, 2):
        ev = crises(t, dt, thresh_ps * 1e-12)
        print(f'\n  crises with dt < {thresh_ps} ps: {len(ev)} events')
        if ev:
            times = np.array([e[0] for e in ev])
            print(f'    first at t={times[0]*1e9:.4f} ns, last at t={times[-1]*1e6:.4f} us')
            if len(ev) > 1:
                gaps = np.diff(times)
                print(f'    spacing between events: median={np.median(gaps)*1e9:.4f} ns  '
                      f'min={gaps.min()*1e9:.4f} ns  max={gaps.max()*1e9:.4f} ns')
                print(f'    median spacing / carrier period = '
                      f'{np.median(gaps)/PERIOD:.4f}')
            deepest = sorted(ev, key=lambda e: e[1])[:6]
            print('    deepest events:')
            for tt, dd, n in deepest:
                print(f'      t={tt*1e9:12.5f} ns  dt={dd*1e12:9.4f} ps  '
                      f'({n} consecutive samples)')
            print('    first 8 events in time order:')
            for tt, dd, n in ev[:8]:
                print(f'      t={tt*1e9:12.5f} ns  dt={dd*1e12:9.4f} ps')
        if thresh_ps == 10:
            summary[label] = {
                'file': path.name, 'points': int(len(t)), 'end_s': float(t[-1]),
                'dt_min_s': float(dt.min()), 'dt_median_s': float(np.median(dt)),
                'frac_at_ceiling': float(n_cap / len(dt)),
                'events_lt_10ps': len(ev),
                'first_event_s': float(ev[0][0]) if ev else None,
                'median_spacing_s': float(np.median(np.diff([e[0] for e in ev])))
                if len(ev) > 1 else None,
            }

# ---- the decisive comparison: how deep is the 225.8 ns crisis, and is it first?
print()
print('=' * 92)
print('IS ~225.8 ns THE FIRST *HARD* CRISIS, OR JUST ONE OF MANY?')
print('=' * 92)
names, v = read_raw(STG / 'cold_engine_gui_net.raw')
t, dt = v[:, 0], np.diff(v[:, 0])
print(f'  GUI/COM path dies at {GUI_STOP*1e9:.6f} ns')
print()
print(f'  {"window":>26s} {"# dt<50ps":>10s} {"min dt (ps)":>12s} {"at t (ns)":>12s}')
for lo, hi in [(0, 32.26), (32.26, 64.52), (64.52, 96.77), (96.77, 129.03),
               (129.03, 161.29), (161.29, 193.55), (193.55, 225.81),
               (225.81, 258.06), (258.06, 290.32), (290.32, 322.58),
               (322.58, 1000.0)]:
    w = (t[:-1] >= lo * 1e-9) & (t[:-1] < hi * 1e-9)
    if not w.any():
        continue
    dw = dt[w]
    n = int((dw < 50e-12).sum())
    j = int(np.argmin(dw))
    tt = t[:-1][w][j]
    print(f'  {f"{lo:.2f}-{hi:.2f} ns":>26s} {n:10d} {dw.min()*1e12:12.4f} '
          f'{tt*1e9:12.4f}')

print()
print('  carrier period = %.6f ns' % (PERIOD * 1e9))
print('  GUI stop         = %.6f ns = %.4f periods' % (GUI_STOP*1e9, GUI_STOP/PERIOD))
print('  GUI stop / cap   = %.4f' % (GUI_STOP / CAP))

(OUT / 'crisis_history.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
