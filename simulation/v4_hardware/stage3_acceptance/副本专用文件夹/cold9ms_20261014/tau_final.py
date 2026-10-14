"""Read-only: proper tau fit on the SETTLING region only, and an honest
uncertainty statement.

The 1.7-2.2 ms windows sit in the pre-startup flat region (V2 mean ~2.8 mV,
not yet rising), so they must be excluded. The settling tail runs from the
take-off at ~2.36 ms to 9 ms.

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

# Merge into one trajectory; the 9 ms tail continues the same physical run.
tl = np.concatenate([t7, t9]) * 1e3      # ms
ml = np.concatenate([m7, m9]) * 1e3      # mV

print('=' * 100)
print('IDENTIFY THE SETTLING REGION')
print('=' * 100)
print(f'  {"t (ms)":>9s} {"V2 mean (mV)":>14s} {"rising?":>9s}')
flat_end = None
for i in range(1, len(tl)):
    rise = ml[i] - ml[i - 1]
    if rise > 0.05 and flat_end is None:
        flat_end = tl[i]
        print(f'  {tl[i]:9.4f} {ml[i]:14.4f}   <-- TAKE-OFF')
        break
print(f'  take-off at t = {flat_end:.4f} ms; before that the output sits at '
      f'~{ml[tl < flat_end].mean():.4f} mV (not yet started)')
print(f'  so the settling tail is {flat_end:.3f} .. {tl[-1]:.3f} ms '
      f'({len(tl[tl >= flat_end])} cycles)')

print()
print('=' * 100)
print('DRIFT RATE ACROSS THE SETTLING TAIL  (mV/ms, 0.5 ms windows)')
print('=' * 100)
print(f'  {"window (ms)":>17s} {"n":>4s} {"rate (mV/ms)":>14s} {"ln(rate)":>10s}')
pts = []
for lo in np.arange(2.5, 9.0, 0.5):
    w = (tl >= lo) & (tl < lo + 0.5)
    if w.sum() < 3:
        continue
    r = float(np.polyfit(tl[w], ml[w], 1)[0])
    print(f'  {f"{lo:.2f}-{lo+0.5:.2f}":>17s} {int(w.sum()):4d} {r:14.4f} {np.log(r):10.4f}')
    if r > 0:
        pts.append((lo + 0.25, r))

print()
print('=' * 100)
print('EXPONENTIAL FIT ON THE SETTLING TAIL ONLY')
print('=' * 100)


def fit(ps):
    x = np.array([p[0] for p in ps])
    y = np.log(np.array([p[1] for p in ps]))
    A = np.vstack([x, np.ones_like(x)]).T
    s, i0 = np.linalg.lstsq(A, y, rcond=None)[0]
    pr = A @ np.array([s, i0])
    r2 = 1 - np.sum((y - pr) ** 2) / np.sum((y - y.mean()) ** 2)
    return -1 / s, r2, i0


tau_all, r2_all, i0 = fit(pts)
print(f'  all {len(pts)} windows ({pts[0][0]:.2f}-{pts[-1][0]:.2f} ms):')
print(f'    tau = {tau_all:.4f} ms   R^2 = {r2_all:.4f}')
print()
# drop the noisiest early points (the take-off transient)
for drop in (1, 2, 3):
    sub = pts[drop:]
    tau_s, r2_s, _ = fit(sub)
    print(f'  drop first {drop} window(s) ({sub[0][0]:.2f}-{sub[-1][0]:.2f} ms): '
          f'tau = {tau_s:.4f} ms   R^2 = {r2_s:.4f}')

print()
print(f'  => best-estimate tau is in the range {min(tau_all, fit(pts[3:])[0]):.2f}'
      f'..{max(tau_all, fit(pts[3:])[0]):.2f} ms')

print()
print('=' * 100)
print('PROJECTION WITH THE UNCERTAINTY SHOWN')
print('=' * 100)
d9 = float(np.polyfit(tl[tl >= 8.5], ml[tl >= 8.5], 1)[0])
cur = float(ml[tl >= 8.5].mean())
gap = cur - NOMINAL * 1e3
print(f'  drift at 9 ms            = {d9:.4f} mV/ms')
print(f'  V2 mean at 9 ms          = {cur:.4f} mV')
print(f'  accepted nominal         = {NOMINAL*1e3:.4f} mV')
print(f'  gap now                  = {gap:+.4f} mV  ({gap/AMP/10:+.4f} % of amplitude)')
print()
print(f'  {"tau (ms)":>10s} {"residual (mV)":>15s} {"final gap (mV)":>16s} {"% of ampl":>11s} {"0.1% screen":>12s}')
for tau in [1.0, 1.25, 1.5, 2.0, 2.5, tau_all]:
    resid = d9 * tau
    fin = gap + resid
    ok = 'PASS' if abs(fin) < 0.001 * AMP * 1e3 else 'FAIL'
    print(f'  {tau:10.4f} {resid:15.4f} {fin:16.4f} {fin/AMP/10:11.4f} {ok:>12s}')
print()
print(f'  note: the screen threshold in mV is 0.1% x {AMP:.3f} V = '
      f'{0.001*AMP*1e3:.4f} mV')

res = {'tau_all_ms': float(tau_all), 'r2_all': float(r2_all),
       'take_off_ms': float(flat_end),
       'drift_9ms_mV_per_ms': d9, 'gap_now_mV': float(gap),
       'cycles_settling': int((tl >= flat_end).sum()),
       'pts': [[float(p[0]), float(p[1])] for p in pts]}
(OUT / 'tau_final.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'written: {OUT / "tau_final.json"}')
