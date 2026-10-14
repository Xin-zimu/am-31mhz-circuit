"""Read-only comparison of a TSTART tail run against the full-window baseline.

Purpose: verify on THIS host that `tran <tstep> <tstop> <tstart> <tmax> uic`
integrates from t=0 and only *reports* from TSTART -- i.e. that the tail window
is numerically identical to the same window of the full run. Only if that holds
can TSTART be used to cut the saved volume of the long cold-start run.

No simulator calls.
"""
from pathlib import Path
import sys
import json
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_acceptance_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

FULL = RUN / 'TSTART_full20us.raw'
TAIL = RUN / 'TSTART_tail20us.raw'
TSTART = 10e-6
TSTOP = 20e-6

report = {}
for label, p in [('full', FULL), ('tail', TAIL)]:
    if not p.exists():
        print(f'MISSING: {p}')
        sys.exit(0)
    names, v = read_raw(p)
    t = v[:, 0]
    print('=' * 88)
    print(f'{label.upper()}  {p.name}')
    print('=' * 88)
    print(f'  points   = {len(t)}')
    print(f'  start    = {t[0]:.9e} s   ({t[0]*1e6:.6f} us)')
    print(f'  end      = {t[-1]:.9e} s   ({t[-1]*1e6:.6f} us)')
    dt = np.diff(t)
    print(f'  dt min   = {dt.min():.4e} s   dt max = {dt.max():.4e} s')
    print(f'  file MB  = {p.stat().st_size/1e6:.2f}')
    print(f'  vars     = {names}')
    report[label] = {'points': int(len(t)), 'start_s': float(t[0]), 'end_s': float(t[-1]),
                     'dt_min_s': float(dt.min()), 'dt_max_s': float(dt.max()),
                     'file_bytes': p.stat().st_size, 'names': names}
    print()

nf, vf = read_raw(FULL)
nt, vt = read_raw(TAIL)
tf, tt = vf[:, 0], vt[:, 0]

print('=' * 88)
print('TSTART SEMANTICS CHECK')
print('=' * 88)
print(f'  TSTART requested   = {TSTART*1e6:.6f} us')
print(f'  full run starts at = {tf[0]*1e6:.6f} us')
print(f'  tail run starts at = {tt[0]*1e6:.6f} us')
print(f'  => tail begins at TSTART: {abs(tt[0]-TSTART) < 1e-18 or abs(tt[0]-TSTART)/TSTART < 1e-9}')
print()
print(f'  full run ends at   = {tf[-1]*1e6:.6f} us')
print(f'  tail run ends at   = {tt[-1]*1e6:.6f} us')
print(f'  => both reach TSTOP: {abs(tf[-1]-TSTOP) < 1e-12 and abs(tt[-1]-TSTOP) < 1e-12}')
print()

# Align on the overlap window and compare exactly
print('=' * 88)
print('NUMERICAL IDENTITY IN THE OVERLAP WINDOW  [TSTART, TSTOP]')
print('=' * 88)
mask_f = tf >= TSTART - 1e-18
f_t, f_v = tf[mask_f], vf[mask_f]
print(f'  full points in window = {len(f_t)}')
print(f'  tail points           = {len(tt)}')
print()

if len(f_t) == len(tt):
    same_t = np.array_equal(f_t, tt)
    print(f'  time axes byte-identical      : {same_t}')
    if not same_t:
        d = np.abs(f_t - tt)
        print(f'    max |dt| = {d.max():.6e} s  at index {int(np.argmax(d))}')
    print()
    print(f'  {"variable":>12s} {"max abs diff":>16s} {"max rel diff":>16s} {"identical":>10s}')
    for i, nm in enumerate(nf):
        if i >= f_v.shape[1] or i >= vt.shape[1]:
            continue
        a, b = f_v[:, i], vt[:, i]
        ad = np.abs(a - b)
        denom = np.maximum(np.abs(a), 1e-30)
        rd = (ad / denom)
        print(f'  {nm:>12s} {ad.max():16.6e} {rd.max():16.6e} '
              f'{str(np.array_equal(a, b)):>10s}')
        report.setdefault('overlap', {})[nm] = {
            'max_abs_diff': float(ad.max()), 'max_rel_diff': float(rd.max()),
            'identical': bool(np.array_equal(a, b))}
    report['overlap']['time_identical'] = bool(same_t)
    report['overlap']['points'] = int(len(tt))
else:
    print('  point counts differ; comparing on the common time grid instead.')
    common = np.intersect1d(np.round(f_t, 15), np.round(tt, 15))
    print(f'  common timepoints = {len(common)}')
    if len(common):
        ia = np.searchsorted(f_t, common)
        ib = np.searchsorted(tt, common)
        for i, nm in enumerate(nf):
            if i >= f_v.shape[1] or i >= vt.shape[1]:
                continue
            ad = np.abs(f_v[ia, i] - vt[ib, i])
            print(f'  {nm:>12s} max abs diff = {ad.max():.6e}  identical={ad.max()==0}')
            report.setdefault('overlap', {})[nm] = {'max_abs_diff': float(ad.max()),
                                                    'identical': bool(ad.max() == 0)}
        report['overlap']['points'] = int(len(common))
        report['overlap']['grid_matched'] = True

print()
print('=' * 88)
print('SAVING ACHIEVED')
print('=' * 88)
if 'full' in report and 'tail' in report:
    fb, tb = report['full']['file_bytes'], report['tail']['file_bytes']
    print(f'  full .raw = {fb/1e6:8.2f} MB  ({report["full"]["points"]} points)')
    print(f'  tail .raw = {tb/1e6:8.2f} MB  ({report["tail"]["points"]} points)')
    print(f'  reduction = {100*(1-tb/fb):.1f}%   (ratio {fb/tb:.3f}x)')
    report['saving'] = {'full_bytes': fb, 'tail_bytes': tb,
                        'reduction_percent': 100*(1-tb/fb)}
    print()
    print(f'  projected for the 9 ms cold-start run at 1 ns:')
    full_9ms = fb / 20e-6 * 9e-3
    tail_9ms = tb / (TSTOP-TSTART) * 0.5e-3
    print(f'    full 0-9 ms  -> approx {full_9ms/1e6:8.1f} MB')
    print(f'    tail 8.5-9 ms-> approx {tail_9ms/1e6:8.1f} MB')
    print(f'    factor       -> {full_9ms/tail_9ms:.1f}x smaller')

(OUT / 'tstart_comparison.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "tstart_comparison.json"}')
