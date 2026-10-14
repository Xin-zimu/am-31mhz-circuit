"""Read-only: is the cold-start bias actually settling?  Fit the drift decay.

The 5-cycle screen is a weak test when only ~10 output cycles exist in the
window: the span it measures IS the drift across that short window, not noise.
This script measures the drift rate directly and fits its decay.

No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

src = S / 'measure_stage3.py'
syntax = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

FOUT = 20e3          # output frequency ~20 kHz -> 50 us period
AMP = 4.816122


def cycle_means_9ms():
    names, v = read_raw(RUN / 'COLD_9ms_tail.raw')
    t = v[:, 0]
    v1 = v[:, names.index('V(v1)')]
    v2 = v[:, names.index('V(v2)')]
    win = t >= t[-1] - 3e-4
    uni = np.arange(t[win][0], t[-1], 2e-9)
    vin = np.interp(uni, t, v1)
    thr = np.mean(np.percentile(vin, [2, 98]))
    up, _ = crossings(t, v1, thr)
    out = []
    for k in range(len(up) - 1):
        a, b = up[k], up[k + 1]
        g = np.arange(a, b, 2e-9)
        yy = np.interp(g, t, v2)
        out.append(((a + b) / 2, np.trapezoid(yy, g) / (g[-1] - g[0]), a, b))
    return out


def cycle_means_7ms():
    with np.load(K / 'cold_7ms_1ns.npz', allow_pickle=True) as z:
        a = z['data']
        nm = z['names'].tolist()
    t = a[:, 0]
    v1 = a[:, nm.index('V(v1)')]
    v2 = a[:, nm.index('V(v2)')]
    win = t >= t[-1] - 3e-4
    uni = np.arange(t[win][0], t[-1], 2e-9)
    vin = np.interp(uni, t, v1)
    thr = np.mean(np.percentile(vin, [2, 98]))
    up, _ = crossings(t, v1, thr)
    out = []
    for k in range(len(up) - 1):
        a1, b1 = up[k], up[k + 1]
        g = np.arange(a1, b1, 2e-9)
        yy = np.interp(g, t, v2)
        out.append(((a1 + b1) / 2, np.trapezoid(yy, g) / (g[-1] - g[0]), a1, b1))
    return out


print('=' * 100)
print('1. CYCLE MEANS: 7 ms WINDOW vs 9 ms WINDOW')
print('=' * 100)
c7 = cycle_means_7ms()
c9 = cycle_means_9ms()
print(f'  7 ms run: {len(c7)} complete cycles in its trailing 300 us')
for tm, mu, a, b in c7:
    print(f'    t={tm*1e3:.6f} ms   V2 mean = {mu:.9f} V')
print(f'  9 ms run: {len(c9)} complete cycles in its trailing 300 us')
for tm, mu, a, b in c9:
    print(f'    t={tm*1e3:.6f} ms   V2 mean = {mu:.9f} V')

print()
print('=' * 100)
print('2. THE DRIFT RATE -- this is what the 5-cycle span actually measures')
print('=' * 100)
print('  span over N trailing cycles, expressed as a drift rate:')
print(f'  {"dataset":>10s} {"N":>4s} {"span (mV)":>11s} {"time span (us)":>17s} {"rate (mV/ms)":>14s}')
for label, c in [('7 ms', c7), ('9 ms', c9)]:
    for n in (5, len(c)):
        if n > len(c):
            continue
        seg = c[-n:]
        mus = np.array([s[1] for s in seg])
        dur = seg[-1][0] - seg[0][0]
        span = np.ptp(mus) * 1e3
        rate = span / (dur * 1e3)
        print(f'  {label:>10s} {n:4d} {span:11.6f} {dur*1e6:17.1f} {rate:14.4f}')

print()
print('=' * 100)
print('3. EXPONENTIAL SETTLING FIT  (drift rate decaying)')
print('=' * 100)
# rate at 7 ms (from its last cycles) and at 9 ms
seg7 = np.array([s[1] for s in c7[-5:]])
t7 = np.array([s[0] for s in c7[-5:]])
d7 = np.polyfit(t7, seg7, 1)[0] * 1e3      # mV/ms
seg9 = np.array([s[1] for s in c9])
t9 = np.array([s[0] for s in c9])
d9 = np.polyfit(t9, seg9, 1)[0] * 1e3
print(f'  drift at 7 ms window centre ({t7.mean()*1e3:.4f} ms) = {d7:+.4f} mV/ms')
print(f'  drift at 9 ms window centre ({t9.mean()*1e3:.4f} ms) = {d9:+.4f} mV/ms')
dt = (t9.mean() - t7.mean()) * 1e3
if d7 > 0 and d9 > 0:
    tau = dt / np.log(d7 / d9)
    print(f'  ratio d7/d9 = {d7/d9:.3f} over dt = {dt:.4f} ms')
    print(f'  => decay time constant tau = {tau:.4f} ms')
    resid = d9 * tau
    print(f'  => residual bias drift still to come = {resid:.4f} mV')
    print(f'  => as a fraction of amplitude = {resid/AMP/1e3*100:.6f} %')

print()
print('=' * 100)
print('4. DISTANCE TO THE ACCEPTED PRE-CHARGED NOMINAL')
print('=' * 100)
NOMINAL_MEAN = 4.496040582          # from weighted_7ms_review.json
cur = float(np.mean([s[1] for s in c9]))
print(f'  pre-charged nominal V2 mean (S03-03 accepted) = {NOMINAL_MEAN:.9f} V')
print(f'  cold start at 9 ms                            = {cur:.9f} V')
print(f'  difference                                    = {(cur-NOMINAL_MEAN)*1e3:+.4f} mV')
print(f'  as a fraction of amplitude                    = {(cur-NOMINAL_MEAN)/AMP*100:+.4f} %')
print()
print(f'  projected with tau from above:')
if d7 > 0 and d9 > 0:
    tau = dt / np.log(d7 / d9)
    for extra in [1, 2, 5, 10]:
        remaining = (d9 * tau) * (1 - np.exp(-extra / tau))
        print(f'    +{extra:2d} ms  ->  additional {(cur-NOMINAL_MEAN)*1e3 + remaining:+9.4f} mV   '
              f'({((cur-NOMINAL_MEAN)*1e3 + remaining)/AMP/10:+.6f} % of amplitude)')

print()
print('=' * 100)
print('5. VERDICT ON THE 0.1% SCREEN')
print('=' * 100)
five9 = np.ptp([s[1] for s in c9[-5:]]) * 1e3
print(f'  last-5-cycle span at 9 ms = {five9:.6f} mV = {five9/AMP/1e3*100:.6f} % of amplitude')
print(f'  screen threshold          = 0.100000 %')
print(f'  arithmetic verdict        : {"PASS" if five9/AMP/1e3*100 < 0.1 else "FAIL"}')
print()
print('  BUT: the 5-cycle window is only 250 us. With a drift rate of')
print(f'  {d9:.2f} mV/ms, the expected span across 250 us is {d9*0.25:.2f} mV --')
print(f'  which accounts for essentially all of the measured {five9:.2f} mV.')
print('  So this "PASS" measures the shortness of the window, not stability.')

res = {
    'drift_7ms_mV_per_ms': float(d7), 'drift_9ms_mV_per_ms': float(d9),
    'tau_ms': float(dt / np.log(d7 / d9)) if d7 > 0 and d9 > 0 else None,
    'residual_mV': float(d9 * (dt / np.log(d7 / d9))) if d7 > 0 and d9 > 0 else None,
    'nominal_mean_V': NOMINAL_MEAN, 'mean_at_9ms_V': cur,
    'delta_mV': float((cur - NOMINAL_MEAN) * 1e3),
    'five_cycle_span_mV': float(five9),
    'five_cycle_span_pct': float(five9 / AMP / 1e3 * 100),
    'expected_span_from_drift_mV': float(d9 * 0.25),
}
(OUT / 'cold9ms_settling.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "cold9ms_settling.json"}')
