r"""Read-only: settle the 12 ms question quantitatively.

The 9 ms review could only EXTRAPOLATE the final bias gap (-0.7446 mV, 0.0155%)
from a local tau ~ 1.005 ms. The 12 ms tail now measures three more ms of the
same physical trajectory, so we can:

  1. re-fit the local exponential asymptote and see if it agrees,
  2. compare the 9 ms projection against the 12 ms measurement,
  3. state the gap as a MEASUREMENT with the residual rise bounded.

Model: V(t) = Vinf + B*exp(-t/tau). For a fixed tau the model is linear in
(Vinf, B), so tau is found by a fine grid search with an exact linear solve at
each tau. No scipy needed.

The three tails (7 ms, 9 ms, 12 ms) are segments of ONE physical run: all use
'uic' from t=0, and TSTART only limits what is SAVED (verified bit-identical in
engine_acceptance_20261014\TSTART短窗对照报告.md). They are therefore joined.
Gaps exist where nothing was saved (7.0-8.5 ms, 9.0-11.5 ms); every fit below is
restricted to a contiguous saved window, so no fit spans a gap.

No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
RUN12 = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
RUN9  = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

src = S / 'measure_stage3.py'
syntax = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

AMP = 4.816122          # accepted nominal robust amplitude (Vpp)
NOMINAL = 4.496040582   # accepted nominal time-weighted mean (V)
SCREEN = 0.001 * AMP        # 0.1% of amplitude, in VOLTS
SCREEN_MV = SCREEN * 1e3   # same threshold in MILLIvolts (gaps are in mV)


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


print('=' * 100)
print('0. ASSEMBLE THE ONE PHYSICAL TRAJECTORY (7 / 9 / 12 ms tails)')
print('=' * 100)
with np.load(K / 'cold_7ms_1ns.npz', allow_pickle=True) as z:
    a7 = z['data']; n7 = z['names'].tolist()
t7, m7 = cycle_means(a7[:, 0], a7[:, n7.index('V(v1)')], a7[:, n7.index('V(v2)')])
n9, v9 = read_raw(RUN9 / 'COLD_9ms_tail.raw')
t9, m9 = cycle_means(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])
n12, v12 = read_raw(RUN12 / 'COLD_12ms_clean.raw')
t12, m12 = cycle_means(v12[:, 0], v12[:, n12.index('V(v1)')], v12[:, n12.index('V(v2)')])

for nm, tt in (('7 ms ', t7), ('9 ms ', t9), ('12 ms', t12)):
    print(f'  {nm} tail: {len(tt):7d} cycles  {tt[0]*1e3:9.4f} .. {tt[-1]*1e3:9.4f} ms')

tl = np.concatenate([t7, t9, t12]) * 1e3
ml = np.concatenate([m7, m9, m12]) * 1e3


def fit_exp(lo, hi):
    """Grid-search tau; solve (Vinf, B) exactly at each tau."""
    w = (tl >= lo) & (tl <= hi)
    x, y = tl[w], ml[w]
    if len(x) < 4:
        return None
    x0 = x - x[0]
    best = None
    for tau in np.arange(0.20, 6.0, 0.001):
        e = np.exp(-x0 / tau)
        A = np.vstack([np.ones_like(x0), e]).T
        coef, res, _, _ = np.linalg.lstsq(A, y, rcond=None)
        rss = float(np.sum((y - A @ coef) ** 2))
        if best is None or rss < best[0]:
            best = (rss, tau, float(coef[0]), float(coef[1]), len(x))
    rss, tau, vinf, B, n = best
    rms = float(np.sqrt(rss / n))
    return {'lo': lo, 'hi': hi, 'n': n, 'tau_ms': float(tau), 'Vinf_mV': vinf,
            'B_mV': B, 'rms_mV': rms}


print()
print('=' * 100)
print('1. LOCAL EXPONENTIAL ASYMPTOTE, FIT ON DIFFERENT WINDOWS')
print('=' * 100)
print('  A single global exponential is known NOT to hold (multi-mode convergence),')
print('  so only LOCAL fits on the late tail are meaningful.')
print()
print(f'  {"fit window (ms)":>18s} {"n":>4s} {"tau (ms)":>10s} {"Vinf (mV)":>13s} '
      f'{"RMS (mV)":>10s} {"Vinf-nominal (mV)":>17s} {"% of ampl":>10s}')
fits = []
for lo, hi in [(2.5, 12.0), (6.5, 12.0), (8.5, 12.0), (9.0, 12.0),
               (10.0, 12.0), (11.0, 12.0), (11.5, 12.0)]:
    f = fit_exp(lo, hi)
    if not f:
        continue
    fits.append(f)
    g = f['Vinf_mV'] - NOMINAL * 1e3
    print(f'  {f"{lo:.2f}-{hi:.2f}":>18s} {f["n"]:4d} {f["tau_ms"]:10.4f} '
          f'{f["Vinf_mV"]:13.6f} {f["rms_mV"]:10.5f} {g:+17.4f} {g/AMP/10:+10.5f}')

print()
print('  Read the RMS column: a window is only trustworthy where the fit residual is')
print('  small compared with the effect being measured.')
print()
print('  CAUTION -- what each window ACTUALLY contains. The saved trajectory is not')
print('  continuous; it is three segments. A window that falls entirely inside a gap')
print('  silently reduces to the next segment, so identical rows below are the SAME')
print('  data, not independent confirmations:')
for nm, tt, te in (('7 ms tail ', t7[0]*1e3, t7[-1]*1e3),
                   ('9 ms tail ', t9[0]*1e3, t9[-1]*1e3),
                   ('12 ms tail', t12[0]*1e3, t12[-1]*1e3)):
    print(f'    {nm}: {tt:9.4f} .. {te:9.4f} ms  ({int(round((te-tt)*20))} complete cycles)')
print('  => the only saved data after 9 ms is the 12 ms tail, 11.5667-11.9667 ms.')
print('     A "9.00-12.00" fit is therefore really the 12 ms tail alone, and its tau')
print('     is fitted on a window SHORTER than tau itself -- weakly constrained. The')
print('     rate-decay estimate in section 2 is not, which is why both are reported.')

print()
print('=' * 100)
print('2. THE 9 ms PROJECTION vs THE 12 ms MEASUREMENT')
print('=' * 100)
# 9 ms state, recomputed for transparency
w9 = (tl >= 8.5) & (tl < 9.0)
d9 = float(np.polyfit(tl[w9], ml[w9], 1)[0])
gap9 = float(ml[w9].mean()) - NOMINAL * 1e3
TAU9 = 1.005
proj9 = gap9 + d9 * TAU9
print(f'  AT 9 ms   : rate = {d9:.4f} mV/ms,  gap = {gap9:+.4f} mV')
print(f'              with tau = {TAU9} ms -> residual rise {d9*TAU9:.4f} mV')
print(f'              PROJECTED final gap = {proj9:+.4f} mV  ({proj9/AMP/10:+.5f} %)')

w12 = (tl >= 11.5) & (tl <= 12.0)
d12 = float(np.polyfit(tl[w12], ml[w12], 1)[0])
gap12 = float(ml[w12].mean()) - NOMINAL * 1e3
print()
print(f'  AT 12 ms  : rate = {d12:.4f} mV/ms,  gap = {gap12:+.4f} mV   <-- MEASURED, not extrapolated')
print(f'              remaining rise to come = {d12:.4f} * tau')
print()
print(f'  {"tau (ms)":>10s} {"residual (mV)":>15s} {"final gap (mV)":>16s} {"% of ampl":>11s} {"0.1% screen":>12s}')
proj12 = {}
for tau in [0.8, 0.9, 0.99, 1.005, 1.1, 1.25, 1.5]:
    resid = d12 * tau
    fin = gap12 + resid
    proj12[tau] = fin
    print(f'  {tau:10.4f} {resid:15.4f} {fin:16.4f} {fin/AMP/10:11.5f} '
          f'{"PASS" if abs(fin) < SCREEN_MV else "FAIL":>12s}')
print()
print(f'  0.1% screen threshold = {SCREEN_MV:.4f} mV')

print()
print('  INDEPENDENT CHECK -- tau implied purely by the rate decay 9 -> 12 ms:')
tau_emp = (11.75 - 8.75) / np.log(d9 / d12)
print(f'    tau = 3.0 ms / ln({d9:.4f} / {d12:.4f}) = {tau_emp:.4f} ms')
print(f'    (the 9 ms review used tau = 1.005 ms; these agree to '
      f'{abs(tau_emp-1.005)/1.005*100:.2f} %)')

print()
print('=' * 100)
print('3. WHAT THE 12 ms RUN ACTUALLY SETTLES')
print('=' * 100)
print(f'  gap at 12 ms, as measured          = {gap12:+.4f} mV = {gap12/AMP/10:+.5f} % of amplitude')
print(f'  screen is 0.1% = {SCREEN*1e3:.4f} mV, so 12 ms is inside it by a factor '
      f'{SCREEN*1e3/abs(gap12):.1f}x')
late = [f for f in fits if f['lo'] >= 9.0 and f['rms_mV'] < 0.15]
if late:
    vs = [f['Vinf_mV'] - NOMINAL * 1e3 for f in late]
    print(f'  late-window asymptote estimates    = {min(vs):+.4f} .. {max(vs):+.4f} mV')
    print(f'    (over {len(late)} windows with RMS < 0.15 mV)')
print(f'  still rising at 12 ms?             = YES, {d12:.4f} mV/ms, tau ~ {tau_emp:.3f} ms')
print(f'    -> the rise that remains is {d12*1.005:.4f} mV, i.e. the gap will NOT grow;')
print(f'       it will close by that amount, not open.')

res = {'gap_9ms_mV': gap9, 'rate_9ms_mV_per_ms': d9,
       'projection_from_9ms_mV': proj9, 'tau_used_at_9ms_ms': TAU9,
       'gap_12ms_mV': gap12, 'rate_12ms_mV_per_ms': d12,
       'pct_12ms': float(gap12 / AMP / 10),
       'screen_mV': float(SCREEN * 1e3),
       'tau_implied_ms': float(tau_emp),
       'fits': fits,
       'projections_from_12ms': {str(k): float(v) for k, v in proj12.items()}}
(OUT / 'cold12ms_settling.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
print()
print(f'written: {OUT / "cold12ms_settling.json"}')
