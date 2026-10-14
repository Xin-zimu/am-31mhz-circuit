"""Read-only: 9 ms cold-start tail vs the archived 7 ms window.

Same measurement method as measure_stage3.py / audit_evidence.py:
2 ns uniform interpolation, robust amplitude P98-P2, trapezoid time-integrated
mean, last five complete cycles.

Question: does the bias keep drifting after 6.5 ms, or does it settle?
No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import hashlib
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

# reuse the project's own crossing function
src = S / 'measure_stage3.py'
syntax = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

NINE = RUN / 'COLD_9ms_tail.raw'
SEVEN = K / 'cold_7ms_1ns.npz'


def cycles_from_arrays(t, cols, names, n_last=5, grid_ns=2.0):
    """Measure the last n complete output cycles.

    cols is (npoints, nvars); time is column 0, so signals are columns >= 1.
    """
    def col(nm):
        return cols[:, names.index(nm)]

    win = t >= t[-1] - 3e-4
    g0 = t[win][0]
    uniform = np.arange(g0, t[-1], grid_ns * 1e-9)
    vin = np.interp(uniform, t, col('V(v1)'))
    thr = np.mean(np.percentile(vin, [2, 98]))
    up, down = crossings(t, col('V(v1)'), thr)
    rows = []
    for begin, end in list(zip(up[:-1], up[1:]))[-n_last:]:
        grid = np.arange(begin, end, grid_ns * 1e-9)
        falls = down[(down > begin) & (down < end)]
        row = {'start_s': float(begin), 'end_s': float(end),
               'period_s': float(end - begin), 'frequency_hz': float(1 / (end - begin)),
               'duty_percent': float(100 * (falls[0] - begin) / (end - begin))
               if len(falls) == 1 else None}
        for nm in names[1:]:
            colv = col(nm)
            y = np.interp(grid, t, colv)
            lo, hi = np.percentile(y, [2, 98])
            row[nm] = {'mean_v': float(np.trapezoid(y, grid) / (grid[-1] - grid[0])),
                       'robust_vpp': float(hi - lo), 'raw_vpp': float(np.ptp(y))}
        rows.append(row)
    amp = float(np.mean([r['V(v2)']['robust_vpp'] for r in rows]))
    span = float(np.ptp([r['V(v2)']['mean_v'] for r in rows]))
    ampx = float(np.ptp([r['V(v2)']['robust_vpp'] for r in rows]))
    per = np.array([r['period_s'] for r in rows])
    perspan = float(np.ptp(per) / np.mean(per))
    return {'rows': rows, 'summary': {
        'V2_robust_vpp': amp,
        'V2_mean_v': float(np.mean([r['V(v2)']['mean_v'] for r in rows])),
        'V2_mean_span_v': span, 'V2_mean_span_frac': span / amp,
        'V2_vpp_span_v': ampx, 'period_rel_span': perspan,
        'passes_0p1pct': bool(span / amp < 1e-3 and ampx / amp < 1e-3 and perspan < 1e-3),
    }}


print('=' * 100)
print('1. THE 9 ms TAIL RUN')
print('=' * 100)
names9, v9 = read_raw(NINE)
t9 = v9[:, 0]
print(f'  file       : {NINE.name}  ({NINE.stat().st_size/1e6:.2f} MB)')
print(f'  points     : {len(t9)}')
print(f'  start      : {t9[0]*1e3:.6f} ms   (requested TSTART = 8.5 ms)')
print(f'  end        : {t9[-1]*1e3:.6f} ms')
dt9 = np.diff(t9)
print(f'  step: min={dt9.min()*1e12:.4f} ps  median={np.median(dt9)*1e12:.3f} ps  '
      f'max={dt9.max()*1e12:.3f} ps')
print(f'  window     : {(t9[-1]-t9[0])*1e6:.1f} us = {(t9[-1]-t9[0])*31e6:.0f} carrier cycles')
print(f'  columns    : {names9}')
res = {'nine': {'points': int(len(t9)), 'start_s': float(t9[0]), 'end_s': float(t9[-1]),
                'dt_min_s': float(dt9.min()), 'dt_median_s': float(np.median(dt9)),
                'bytes': NINE.stat().st_size}}

print()
print('=' * 100)
print('2. LAST FIVE COMPLETE CYCLES AT 9 ms  (same method as the 7 ms review)')
print('=' * 100)
r9 = cycles_from_arrays(t9, v9, names9)
print(f'  {"cycle":>5s} {"start (ms)":>12s} {"end (ms)":>12s} {"period (us)":>12s} '
      f'{"freq (Hz)":>12s} {"duty %":>8s} {"V2 mean (V)":>13s} {"V2 vpp (V)":>12s}')
for i, r in enumerate(r9['rows'], 1):
    print(f'  {i:5d} {r["start_s"]*1e3:12.6f} {r["end_s"]*1e3:12.6f} '
          f'{r["period_s"]*1e6:12.6f} {r["frequency_hz"]:12.3f} '
          f'{(r["duty_percent"] or float("nan")):8.4f} '
          f'{r["V(v2)"]["mean_v"]:13.6f} {r["V(v2)"]["robust_vpp"]:12.6f}')
s9 = r9['summary']
print()
for k, v in s9.items():
    print(f'  {k:24s} = {v}')
res['nine_summary'] = s9

print()
print('=' * 100)
print('3. THE DECISIVE COMPARISON: 7 ms vs 9 ms  (identical method)')
print('=' * 100)
with np.load(SEVEN, allow_pickle=True) as z:
    a7 = z['data']
    n7 = z['names'].tolist()
r7 = cycles_from_arrays(a7[:, 0], a7, n7)
s7 = r7['summary']

print(f'  {"quantity":30s} {"7 ms (archived)":>20s} {"9 ms (new tail)":>20s} {"change":>14s}')
for key, label, fmt in [
        ('V2_robust_vpp', 'V2 robust amplitude (Vpp)', '{:.9f}'),
        ('V2_mean_v', 'V2 time-weighted mean (V)', '{:.9f}'),
        ('V2_mean_span_v', 'V2 cycle-mean span (mV)', None),
        ('V2_mean_span_frac', 'span / amplitude (%)', None),
        ('V2_vpp_span_v', 'V2 amplitude span (mV)', None),
        ('period_rel_span', 'period relative span (%)', None)]:
    a, b = s7[key], s9[key]
    if key in ('V2_mean_span_v', 'V2_vpp_span_v'):
        sa, sb = f'{a*1e3:.6f} mV', f'{b*1e3:.6f} mV'
    elif key in ('V2_mean_span_frac', 'period_rel_span'):
        sa, sb = f'{a*100:.6f} %', f'{b*100:.6f} %'
    else:
        sa, sb = fmt.format(a), fmt.format(b)
    ch = f'{(b-a)/a*100:+.2f}%' if a else 'n/a'
    print(f'  {label:30s} {sa:>20s} {sb:>20s} {ch:>14s}')

print()
print(f'  0.1% temporary repeatability screen:')
print(f'    7 ms : {"PASS" if s7["passes_0p1pct"] else "FAIL"}')
print(f'    9 ms : {"PASS" if s9["passes_0p1pct"] else "FAIL"}')
res['seven_summary'] = s7

print()
print('=' * 100)
print('4. IS THE BIAS STILL RISING?  (V2 mean across the window)')
print('=' * 100)
m = t9 >= t9[-1] - 1e-5
tt, vv = t9[m], v9[m, names9.index('V(v2)')]
print(f'  last 10 us of the 9 ms run, V(v2) mean in 1 us bins:')
print(f'  {"window (ms)":>18s} {"mean V(v2) (V)":>16s} {"change (mV)":>13s}')
prev = None
for lo in np.arange(8.99, 9.0001, 0.001):
    w = (tt >= (lo - 0.001)) & (tt < lo)
    if w.sum() < 3:
        continue
    mu = float(vv[w].mean())
    d = '' if prev is None else f'{(mu-prev)*1e3:+.4f}'
    print(f'  {f"{lo-0.001:.3f}-{lo:.3f}":>18s} {mu:16.9f} {d:>13s}')
    prev = mu

(OUT / 'cold9ms_analysis.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
print()
print(f'written: {OUT / "cold9ms_analysis.json"}')
print(f'sha256(9ms raw) = {hashlib.sha256(NINE.read_bytes()).hexdigest()}')
