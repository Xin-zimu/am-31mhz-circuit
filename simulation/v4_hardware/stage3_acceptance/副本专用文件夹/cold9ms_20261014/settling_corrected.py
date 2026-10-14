"""Read-only, CORRECTED: settling analysis of the 9 ms cold-start tail.

Fixes a unit error in the first pass (polyfit over seconds reported as mV/ms).
Derives the drift rate in mV/ms directly, fits the decay, and projects the
residual bias drift.

No simulator calls. Nothing on disk is modified.
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
NOMINAL = 4.496040582          # S03-03 accepted pre-charged V2 time-weighted mean


def cycles(t, v1, v2, tmax=None):
    """Return [(mid_time_s, cycle_mean_V)] for every complete output cycle."""
    hi = tmax if tmax is not None else t[-1]
    win = t >= hi - 3e-4
    uni = np.arange(t[win][0], hi, 2e-9)
    thr = np.mean(np.percentile(np.interp(uni, t, v1), [2, 98]))
    up, _ = crossings(t, v1, thr)
    up = up[up <= hi]
    out = []
    for k in range(len(up) - 1):
        a, b = up[k], up[k + 1]
        g = np.arange(a, b, 2e-9)
        yy = np.interp(g, t, v2)
        out.append(((a + b) / 2, float(np.trapezoid(yy, g) / (g[-1] - g[0])), a, b))
    return out


def drift_mV_per_ms(rows):
    """Slope of cycle-mean vs time, in mV per millisecond."""
    ts = np.array([r[0] for r in rows]) * 1e3      # ms
    ms = np.array([r[1] for r in rows]) * 1e3      # mV
    if len(ts) < 2:
        return float('nan')
    return float(np.polyfit(ts, ms, 1)[0])


print('=' * 100)
print('LOAD DATA')
print('=' * 100)
n9, v9 = read_raw(RUN / 'COLD_9ms_tail.raw')
c9 = cycles(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])
print(f'  9 ms tail : {len(c9)} complete cycles, '
      f'{c9[0][0]*1e3:.6f} .. {c9[-1][0]*1e3:.6f} ms')

with np.load(K / 'cold_7ms_1ns.npz', allow_pickle=True) as z:
    a7 = z['data']
    n7 = z['names'].tolist()
# The 7 ms archive is the FULL run; take only its trailing window.
c7_all = cycles(a7[:, 0], a7[:, n7.index('V(v1)')], a7[:, n7.index('V(v2)')])
c7 = [r for r in c7_all if r[0] > 6.7e-3]
print(f'  7 ms run  : {len(c7_all)} cycles total; using {len(c7)} in 6.7-7.0 ms')

print()
print('=' * 100)
print('1. DRIFT RATE AT EACH WINDOW  (correct units: mV per ms)')
print('=' * 100)
d7 = drift_mV_per_ms(c7)
d9 = drift_mV_per_ms(c9)
print(f'  drift at 7.0 ms = {d7:9.4f} mV/ms')
print(f'  drift at 9.0 ms = {d9:9.4f} mV/ms')
print(f'  ratio           = {d7/d9:9.4f}  over {(c9[-1][0]-c7[-1][0])*1e3:.4f} ms')

dt_ms = (np.mean([r[0] for r in c9]) - np.mean([r[0] for r in c7])) * 1e3
tau = dt_ms / np.log(d7 / d9)
print(f'  decay time constant tau = {tau:.4f} ms')

print()
print('=' * 100)
print('2. WHAT THE 0.1% SCREEN ACTUALLY MEASURED AT 9 ms')
print('=' * 100)
five = np.array([r[1] for r in c9[-5:]])
span = float(np.ptp(five)) * 1e3
win_ms = (c9[-1][0] - c9[-5][0]) * 1e3
print(f'  last-5-cycle span      = {span:.6f} mV')
print(f'  window length          = {win_ms:.4f} ms')
print(f'  span / amplitude       = {span/AMP/1e3*100:.6f} %   (screen: 0.1 %)')
print(f'  arithmetic verdict     = {"PASS" if span/AMP/1e3*100 < 0.1 else "FAIL"}')
print()
print(f'  drift alone predicts a span of d9 * {win_ms:.4f} ms = {d9*win_ms:.4f} mV')
print(f'  measured span          = {span:.4f} mV')
print(f'  => the screen measured the DRIFT ACROSS A SHORT WINDOW, not settling.')
print(f'  => shortening the window always "passes" this screen. It is not a')
print(f'     stability proof at any fixed window length.')

print()
print('=' * 100)
print('3. IS THE BIAS STILL RISING?')
print('=' * 100)
print(f'  {"cycle t (ms)":>14s} {"V2 mean (V)":>15s} {"step vs prev (uV)":>19s}')
prev = None
for tm, mu, a, b in c9:
    s = '' if prev is None else f'{(mu-prev)*1e6:+19.3f}'
    print(f'  {tm*1e3:14.6f} {mu:15.9f} {s}')
    prev = mu
print()
print(f'  monotonic rise across all {len(c9)} cycles: '
      f'{bool(np.all(np.diff([r[1] for r in c9]) > 0))}')

print()
print('=' * 100)
print('4. PROJECTION: WHERE DOES IT LAND?')
print('=' * 100)
cur = float(np.mean([r[1] for r in c9]))
delta = (cur - NOMINAL) * 1e3
resid = d9 * tau
print(f'  amplitude (robust Vpp)                 = {AMP:.6f} V')
print(f'  accepted pre-charged nominal V2 mean   = {NOMINAL:.9f} V')
print(f'  cold start V2 mean at 9 ms             = {cur:.9f} V')
print(f'  gap to nominal now                     = {delta:+.4f} mV '
      f'({delta/AMP/10:+.4f} % of amplitude)')
print()
print(f'  with an exponential decay of rate (tau = {tau:.4f} ms),')
print(f'  the drift still to come after 9 ms     = d9 * tau = {resid:+.4f} mV')
print(f'  projected final value                  = {cur*1e3 + resid:.4f} mV '
      f'= {(cur*1e3+resid)/1e3:.9f} V')
print(f'  projected final gap to nominal         = {delta + resid:+.4f} mV '
      f'({(delta+resid)/AMP/10:+.4f} % of amplitude)')
print()
print('  projected gap at later horizons:')
for extra in [1, 2, 5, 10, 20]:
    add = resid * (1 - np.exp(-extra / tau))
    print(f'    +{extra:2d} ms  ->  {delta + add:+9.4f} mV   '
          f'({(delta+add)/AMP/10:+.4f} % of amplitude)')

print()
print('=' * 100)
print('5. VERDICT')
print('=' * 100)
print(f'  1. The bias is STILL RISING at 9 ms, monotonically, at {d9:.2f} mV/ms.')
print(f'  2. The rise is decaying with tau ~ {tau:.2f} ms -- a genuine settling tail.')
print(f'  3. The 0.1% last-five-cycle screen PASSES at 9 ms, but that PASS is an')
print(f'     artifact of the window being short relative to tau.')
print(f'  4. Extrapolated residual is ~{resid:.1f} mV, which would bring the output')
print(f'     to within ~{abs(delta+resid):.1f} mV of the accepted nominal.')

res = {
    'drift_7ms_mV_per_ms': d7, 'drift_9ms_mV_per_ms': d9, 'tau_ms': float(tau),
    'n_cycles_9ms': len(c9),
    'last5_span_mV': span, 'last5_window_ms': float(win_ms),
    'last5_span_pct': float(span / AMP / 1e3 * 100),
    'drift_predicted_span_mV': float(d9 * win_ms),
    'mean_at_9ms_V': cur, 'nominal_V': NOMINAL,
    'gap_mV': float(delta), 'residual_mV': float(resid),
    'projected_final_gap_mV': float(delta + resid),
    'monotonic_rise': bool(np.all(np.diff([r[1] for r in c9]) > 0)),
    'cycles_9ms': [[float(r[0]), float(r[1])] for r in c9],
    'cycles_7ms_tail': [[float(r[0]), float(r[1])] for r in c7],
}
(OUT / 'cold9ms_settling_corrected.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "cold9ms_settling_corrected.json"}')
