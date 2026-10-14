"""Read-only: 12 ms cold-start tail, measured with the SAME method as the
9 ms / 7 ms reviews so the numbers are directly comparable.

2 ns uniform interpolation, robust amplitude P98-P2, trapezoid time-integrated
mean, last five complete cycles. Plus the drift-rate diagnostic, which is the
only thing that actually resolves "settled" vs "still converging".

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
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

# reuse the project's own crossing function
src = S / 'measure_stage3.py'
syntax = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

TWELVE = RUN / 'COLD_12ms_clean.raw'
NINE   = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014') / 'COLD_9ms_tail.raw'
SEVEN  = K / 'cold_7ms_1ns.npz'

AMP = 4.816122          # accepted nominal robust amplitude (Vpp)
NOMINAL = 4.496040582   # accepted nominal time-weighted mean (V)


def cycles_from_arrays(t, cols, names, n_last=5, grid_ns=2.0):
    """cols is (npoints, nvars); time is column 0, signals are columns >= 1."""
    def col(nm):
        return cols[:, names.index(nm)]

    g0 = t[max(0, np.searchsorted(t, t[-1] - 3e-4))]
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


def cycle_means(t, v1, v2):
    """Time-weighted mean of one full output cycle per input period."""
    uni = np.arange(t[0], t[-1], 2e-9)
    thr = np.mean(np.percentile(np.interp(uni, t, v1), [2, 98]))
    up, _ = crossings(t, v1, thr)
    ts, ms = [], []
    for k in range(len(up) - 1):
        a, b = up[k], up[k + 1]
        g = np.arange(a, b, 2e-9)
        ts.append((a + b) / 2)
        ms.append(float(np.trapezoid(np.interp(g, t, v2), g) / (g[-1] - g[0])))
    return np.array(ts), np.array(ms)


res = {}

print('=' * 100)
print('1. THE 12 ms TAIL RUN')
print('=' * 100)
names, vals = read_raw(TWELVE)
t = vals[:, 0]
dt = np.diff(t)
print(f'  file       : {TWELVE.name}  ({TWELVE.stat().st_size/1e6:.2f} MB)')
print(f'  points     : {len(t)}')
print(f'  start      : {t[0]*1e3:.6f} ms   (requested TSTART = 11.5 ms)')
print(f'  end        : {t[-1]*1e3:.6f} ms')
print(f'  step: min={dt.min()*1e12:.4f} ps  median={np.median(dt)*1e12:.3f} ps  max={dt.max()*1e12:.3f} ps')
print(f'  window     : {(t[-1]-t[0])*1e6:.1f} us = {(t[-1]-t[0])*31e6:.0f} carrier cycles')
print(f'  columns    : {names}')
res['twelve'] = {'points': int(len(t)), 'start_s': float(t[0]), 'end_s': float(t[-1]),
                 'dt_min_s': float(dt.min()), 'dt_median_s': float(np.median(dt)),
                 'dt_max_s': float(dt.max()), 'bytes': TWELVE.stat().st_size,
                 'sha256': hashlib.sha256(TWELVE.read_bytes()).hexdigest()}

print()
print('=' * 100)
print('2. LAST FIVE COMPLETE CYCLES AT 12 ms')
print('=' * 100)
r12 = cycles_from_arrays(t, vals, names)
print(f'  {"cycle":>5s} {"start (ms)":>12s} {"end (ms)":>12s} {"period (us)":>12s} '
      f'{"freq (Hz)":>12s} {"duty %":>8s} {"V2 mean (V)":>13s} {"V2 vpp (V)":>12s}')
for i, r in enumerate(r12['rows'], 1):
    print(f'  {i:5d} {r["start_s"]*1e3:12.6f} {r["end_s"]*1e3:12.6f} '
          f'{r["period_s"]*1e6:12.6f} {r["frequency_hz"]:12.3f} '
          f'{(r["duty_percent"] or float("nan")):8.4f} '
          f'{r["V(v2)"]["mean_v"]:13.6f} {r["V(v2)"]["robust_vpp"]:12.6f}')
s12 = r12['summary']
print()
for k, v in s12.items():
    print(f'  {k:24s} = {v}')
res['twelve_summary'] = s12

print()
print('=' * 100)
print('3. 7 ms vs 9 ms vs 12 ms  (identical method)')
print('=' * 100)
with np.load(SEVEN, allow_pickle=True) as z:
    a7 = z['data']; n7 = z['names'].tolist()
s7 = cycles_from_arrays(a7[:, 0], a7, n7)['summary']

n9, v9 = read_raw(NINE)
s9 = cycles_from_arrays(v9[:, 0], v9, n9)['summary']

print(f'  {"quantity":30s} {"7 ms":>18s} {"9 ms":>18s} {"12 ms":>18s} {"9->12 %":>10s}')
for key, label, fmt in [
        ('V2_robust_vpp', 'V2 robust amplitude (Vpp)', '{:.9f}'),
        ('V2_mean_v', 'V2 time-weighted mean (V)', '{:.9f}'),
        ('V2_mean_span_v', 'V2 cycle-mean span', None),
        ('V2_mean_span_frac', 'span / amplitude', None),
        ('V2_vpp_span_v', 'V2 amplitude span', None),
        ('period_rel_span', 'period relative span', None)]:
    def show(x):
        if key in ('V2_mean_span_v', 'V2_vpp_span_v'):
            return f'{x*1e3:.6f} mV'
        if key in ('V2_mean_span_frac', 'period_rel_span'):
            return f'{x*100:.6f} %'
        return fmt.format(x)
    ch = f'{(s12[key]-s9[key])/s9[key]*100:+.3f}%' if s9[key] else 'n/a'
    print(f'  {label:30s} {show(s7[key]):>18s} {show(s9[key]):>18s} {show(s12[key]):>18s} {ch:>10s}')

print()
print('  0.1% temporary repeatability screen:')
for nm, s in (('7 ms', s7), ('9 ms', s9), ('12 ms', s12)):
    print(f'    {nm:6s}: {"PASS" if s["passes_0p1pct"] else "FAIL"}')
res['seven_summary'] = s7
res['nine_summary'] = s9

print()
print('=' * 100)
print('4. IS THE BIAS STILL RISING?  (V2 time-weighted mean per cycle)')
print('=' * 100)
t7, m7 = cycle_means(a7[:, 0], a7[:, n7.index('V(v1)')], a7[:, n7.index('V(v2)')])
t9, m9 = cycle_means(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])
t12, m12 = cycle_means(t, vals[:, names.index('V(v1)')], vals[:, names.index('V(v2)')])

tl = np.concatenate([t7, t9, t12]) * 1e3
ml = np.concatenate([m7, m9, m12]) * 1e3

print(f'  {"window (ms)":>17s} {"n":>4s} {"rate (mV/ms)":>14s}')
rates_12 = []
for lo in np.arange(9.0, 12.0, 0.5):
    w = (tl >= lo) & (tl < lo + 0.5)
    if w.sum() < 3:
        continue
    r = float(np.polyfit(tl[w], ml[w], 1)[0])
    print(f'  {f"{lo:.2f}-{lo+0.5:.2f}":>17s} {int(w.sum()):4d} {r:14.4f}')
    rates_12.append((lo + 0.25, r))

d12 = float(np.polyfit(tl[tl >= 11.5], ml[tl >= 11.5], 1)[0])
cur12 = float(ml[tl >= 11.5].mean())
gap12 = cur12 - NOMINAL * 1e3
print()
print(f'  drift rate at 11.5-12 ms   = {d12:.4f} mV/ms')
print(f'  V2 mean at 12 ms           = {cur12:.4f} mV')
print(f'  accepted nominal           = {NOMINAL*1e3:.4f} mV')
print(f'  gap now                    = {gap12:+.4f} mV  ({gap12/AMP/10:+.4f} % of amplitude)')
res['drift_12ms_mV_per_ms'] = d12
res['V2_mean_12ms_mV'] = cur12
res['gap_12ms_mV'] = gap12
res['rates_9to12'] = [[float(a), float(b)] for a, b in rates_12]

print()
print('=' * 100)
print('5. EFFECTIVE tau NOW THAT THE 9-12 ms DECADE IS OBSERVED')
print('=' * 100)
# drift-rate decay across the whole settling tail: 9 ms window vs 11.5-12 ms window
d9w = float(np.polyfit(tl[(tl >= 8.5) & (tl < 9.0)], ml[(tl >= 8.5) & (tl < 9.0)], 1)[0])
print(f'  rate 8.5-9.0 ms   = {d9w:.4f} mV/ms')
print(f'  rate 11.5-12.0 ms = {d12:.4f} mV/ms')
if d12 > 0 and d9w > 0:
    # r(t) ~ exp(-t/tau): ln(r2/r1) = -(t2-t1)/tau, with window centres
    # 8.75 ms (8.5-9.0) and 11.75 ms (11.5-12.0), so dt = 3.0 ms.
    tau_emp = (11.75 - 8.75) / np.log(d9w / d12)
    print(f'  implied tau from rate decay over 3.0 ms = {tau_emp:.4f} ms')
    res['tau_implied_ms'] = float(tau_emp)
    resid = d12 * tau_emp
    fin = gap12 + resid
    print(f'  residual rise still to come = d12 * tau = {resid:.4f} mV')
    print(f'  projected final gap         = {fin:+.4f} mV  ({fin/AMP/10:+.4f} % of amplitude)')
    print(f'  0.1% screen (threshold {0.001*AMP*1e3:.4f} mV): '
          f'{"PASS" if abs(fin) < 0.001*AMP*1e3 else "FAIL"}')
    res['projected_final_gap_mV'] = float(fin)
    res['projected_final_gap_pct'] = float(fin/AMP/10)

(OUT / 'cold12ms_analysis.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
print()
print(f'written: {OUT / "cold12ms_analysis.json"}')
