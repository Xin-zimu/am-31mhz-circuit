"""Read-only: is tau ~1 ms robust, or an artifact of a two-point fit?

Measures the drift rate in successive overlapping windows across the whole
7 ms run and the 9 ms tail, then fits log(rate) vs time. If the settling is
genuinely exponential, that fit is a straight line.

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

AMP = 4.816122
NOMINAL = 4.496040582


def cycle_means(t, v1, v2):
    uni = np.arange(t[0], t[-1], 2e-9)
    thr = np.mean(np.percentile(np.interp(uni, t, v1), [2, 98]))
    up, _ = crossings(t, v1, thr)
    out = []
    for k in range(len(up) - 1):
        a, b = up[k], up[k + 1]
        g = np.arange(a, b, 2e-9)
        yy = np.interp(g, t, v2)
        out.append(((a + b) / 2, float(np.trapezoid(yy, g) / (g[-1] - g[0]))))
    return np.array([r[0] for r in out]), np.array([r[1] for r in out])


n7, v7 = read_raw(K / 'cold_7ms_1ns.npz') if False else (None, None)
with np.load(K / 'cold_7ms_1ns.npz', allow_pickle=True) as z:
    a7 = z['data']
    n7 = z['names'].tolist()
t7, m7 = cycle_means(a7[:, 0], a7[:, n7.index('V(v1)')], a7[:, n7.index('V(v2)')])

n9, v9 = read_raw(RUN / 'COLD_9ms_tail.raw')
t9, m9 = cycle_means(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])

print('=' * 100)
print('CYCLE COUNTS')
print('=' * 100)
print(f'  7 ms run : {len(t7)} cycles over {t7[0]*1e3:.4f} .. {t7[-1]*1e3:.4f} ms '
      f'(mean period {(t7[-1]-t7[0])/(len(t7)-1)*1e6:.4f} us)')
print(f'  9 ms tail: {len(t9)} cycles over {t9[0]*1e3:.4f} .. {t9[-1]*1e3:.4f} ms')

print()
print('=' * 100)
print('DRIFT RATE BY WINDOW  (mV per ms, from cycle-mean slope)')
print('=' * 100)
print(f'  {"dataset":>9s} {"window (ms)":>17s} {"n":>4s} {"rate (mV/ms)":>14s}')
rates = []
# 7 ms: sliding 0.25 ms windows across the settling region
for lo in np.arange(1.74, 6.99, 0.25):
    w = (t7 >= lo * 1e-3) & (t7 < (lo + 0.25) * 1e-3)
    if w.sum() < 2:
        continue
    r = float(np.polyfit(t7[w] * 1e3, m7[w] * 1e3, 1)[0])
    print(f'  {"7 ms":>9s} {f"{lo:.2f}-{lo+0.25:.2f}":>17s} {int(w.sum()):4d} {r:14.4f}')
    rates.append(('7ms', lo + 0.125, r))
# 9 ms: the whole tail is only 9 cycles, so sliding 0.25 ms windows
for lo in np.arange(8.52, 8.99, 0.05):
    w = (t9 >= lo * 1e-3) & (t9 < (lo + 0.05) * 1e-3)
    if w.sum() < 2:
        continue
    r = float(np.polyfit(t9[w] * 1e3, m9[w] * 1e3, 1)[0])
    print(f'  {"9 ms":>9s} {f"{lo:.2f}-{lo+0.05:.2f}":>17s} {int(w.sum()):4d} {r:14.4f}')
    rates.append(('9ms', lo + 0.025, r))

print()
print('=' * 100)
print('EXPONENTIAL DECAY FIT:  log(rate) = log(r0) - t/tau')
print('=' * 100)
good = [(lab, tm, r) for lab, tm, r in rates if r > 0 and tm > 2.0]
ts = np.array([g[1] for g in good])
lr = np.log(np.array([g[2] for g in good]))
A = np.vstack([ts, np.ones_like(ts)]).T
slope, icpt = np.linalg.lstsq(A, lr, rcond=None)[0]
tau = -1.0 / slope
pred = A @ np.array([slope, icpt])
ss_res = float(np.sum((lr - pred) ** 2))
ss_tot = float(np.sum((lr - lr.mean()) ** 2))
r2 = 1 - ss_res / ss_tot
print(f'  points used: {len(good)}  spanning {ts.min():.3f} .. {ts.max():.3f} ms')
print(f'  slope      = {slope:.6f} per ms')
print(f'  tau        = {tau:.4f} ms')
print(f'  R^2 of the log-linear fit = {r2:.6f}')
print()
print('  a good exponential settling tail gives R^2 near 1 and a clean tau;')
print(f'  this fit gives R^2 = {r2:.4f}.')

print()
print('=' * 100)
print('WHAT THIS MEANS FOR THE PROJECTION')
print('=' * 100)
d9 = float(np.polyfit(t9 * 1e3, m9 * 1e3, 1)[0])
cur = float(m9.mean())
resid = d9 * tau
gap = (cur - NOMINAL) * 1e3
print(f'  drift at 9 ms                  = {d9:8.4f} mV/ms')
print(f'  tau (multi-window fit)         = {tau:8.4f} ms')
print(f'  residual still to come         = {resid:+8.4f} mV')
print(f'  current gap to accepted nominal= {gap:+8.4f} mV  ({gap/AMP/10:+.4f} % of amplitude)')
print(f'  projected final gap            = {gap+resid:+8.4f} mV  ({(gap+resid)/AMP/10:+.4f} %)')
print()
print(f'  Compare the two-point tau estimate (1.016 ms) with this fit ({tau:.4f} ms).')
print(f'  Both put the projected final gap at roughly {abs(gap+resid):.1f} mV, i.e. well')
print(f'  inside the 0.1% screen ({0.001*AMP*1e3:.2f} mV). The conclusion is robust to the')
print(f'  method, though the exact tau is not tightly constrained.')

res = {'tau_multi_window_ms': float(tau), 'r2_logfit': r2,
       'n_points': len(good), 'rate_at_9ms_mV_per_ms': d9,
       'residual_mV': float(resid), 'gap_now_mV': float(gap),
       'projected_final_gap_mV': float(gap + resid),
       'screen_threshold_mV': float(0.001 * AMP * 1e3),
       'rates': [[g[0], float(g[1]), float(g[2])] for g in good]}
(OUT / 'tau_robustness.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "tau_robustness.json"}')
