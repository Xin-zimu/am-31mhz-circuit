"""Read-only: direct 3-parameter exponential fit for the settling asymptote.

Fits V2(t) = V_inf + A*exp(-t/tau) to the cycle means of the merged
7 ms + 9 ms trajectory, so the projected final value does not depend on a
separately estimated tau.

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
syn = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syn.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

AMP = 4.816122
NOMINAL = 4.496040582


def cycle_means(t, v1, v2):
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


with np.load(K / 'cold_7ms_1ns.npz', allow_pickle=True) as z:
    a7 = z['data']; n7 = z['names'].tolist()
t7, m7 = cycle_means(a7[:, 0], a7[:, n7.index('V(v1)')], a7[:, n7.index('V(v2)')])
n9, v9 = read_raw(RUN / 'COLD_9ms_tail.raw')
t9, m9 = cycle_means(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])

tl = np.concatenate([t7, t9]) * 1e3
ml = np.concatenate([m7, m9]) * 1e3

# settling region: from take-off until the end
mask = tl >= 2.4
x, y = tl[mask], ml[mask]
print('=' * 100)
print('DIRECT EXPONENTIAL FIT   V2(t) = V_inf + A*exp(-t/tau)')
print('=' * 100)
print(f'  fitted on {len(x)} cycles from {x[0]:.3f} to {x[-1]:.3f} ms')

# grid search over tau, linear least squares for V_inf and A at each tau
best = None
for tau in np.arange(0.4, 4.0, 0.001):
    e = np.exp(-x / tau)
    A = np.vstack([np.ones_like(x), e]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = float(np.sum((y - A @ coef) ** 2))
    if best is None or r < best[0]:
        best = (r, tau, coef)
r, tau, coef = best
vinf, amp = coef
rms = np.sqrt(r / len(x))
print(f'  tau     = {tau:.4f} ms')
print(f'  V_inf   = {vinf:.6f} mV  = {vinf/1e3:.9f} V')
print(f'  A       = {amp:.4f} mV')
print(f'  RMS residual = {rms:.4f} mV')

print()
print('=' * 100)
print('CONVERGENCE OF THE FIT')
print('=' * 100)
print(f'  {"tau grid":>12s} {"V_inf (mV)":>14s} {"RMS (mV)":>11s}')
for tt in [0.5, 0.8, 1.0, 1.01, 1.05, 1.1, 1.2, 1.5, 2.0, 3.0]:
    e = np.exp(-x / tt)
    A = np.vstack([np.ones_like(x), e]).T
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    rr = np.sqrt(np.sum((y - A @ c) ** 2) / len(x))
    mark = '  <-- best' if abs(tt - tau) < 0.006 else ''
    print(f'  {tt:12.4f} {c[0]:14.6f} {rr:11.4f}{mark}')

print()
print('=' * 100)
print('THE ANSWER THIS PROJECT NEEDED')
print('=' * 100)
print(f'  accepted pre-charged nominal V2 mean = {NOMINAL*1e3:.6f} mV')
print(f'  cold-start settled asymptote         = {vinf:.6f} mV')
print(f'  difference                           = {vinf - NOMINAL*1e3:+.4f} mV')
print(f'  as a fraction of amplitude           = {(vinf - NOMINAL*1e3)/AMP/10:+.4f} %')
print()
print(f'  time to reach within 1 mV of asymptote: '
      f'{tau*np.log(abs(amp)/1.0):.4f} ms after take-off (t ~ '
      f'{2.4 + tau*np.log(abs(amp)/1.0):.3f} ms)')
print(f'  time to reach within 0.1% of amplitude (4.82 mV): '
      f'{tau*np.log(abs(amp)/4.816):.4f} ms -> t ~ '
      f'{2.4 + tau*np.log(abs(amp)/4.816):.3f} ms')
print()
print(f'  drift rate at 9 ms implied by the fit = '
      f'{abs(amp)*np.exp(-9.0/tau)/tau:.4f} mV/ms')
print(f'  (measured directly                    = 11.9058 mV/ms)')

res = {
    'tau_ms': float(tau), 'V_inf_mV': float(vinf), 'A_mV': float(amp),
    'rms_mV': float(rms), 'n_cycles': int(len(x)),
    'nominal_mV': NOMINAL * 1e3,
    'asymptote_vs_nominal_mV': float(vinf - NOMINAL * 1e3),
    'asymptote_vs_nominal_pct': float((vinf - NOMINAL * 1e3) / AMP / 10),
    't_within_1mV_ms': float(2.4 + tau * np.log(abs(amp) / 1.0)),
    't_within_screen_ms': float(2.4 + tau * np.log(abs(amp) / 4.816)),
    'implied_drift_9ms_mV_per_ms': float(abs(amp) * np.exp(-9.0 / tau) / tau),
}
(OUT / 'asymptote_fit.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "asymptote_fit.json"}')
