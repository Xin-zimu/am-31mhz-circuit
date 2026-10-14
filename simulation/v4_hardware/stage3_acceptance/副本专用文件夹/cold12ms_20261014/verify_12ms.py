"""Read-only: verify the 12 ms result and check the documented traps.

Deliberately re-runs the same trap checks the 9 ms review needed:
  1. The last-five-cycles 0.1% screen is a NOISY, window-length-dependent
     estimator -- shortening the window can always pass it. So it is reported
     but never used alone.
  2. The real evidence is the DRIFT RATE and whether it keeps decaying.
  3. Full-window (not last-5) span, to show convergence rather than a cherry-picked
     window.

No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

src = S / 'measure_stage3.py'
syntax = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

TWELVE = RUN / 'COLD_12ms_clean.raw'
NINE   = Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014') / 'COLD_9ms_tail.raw'
SEVEN  = K / 'cold_7ms_1ns.npz'
AMP = 4.816122

def col_of(v, names, nm):
    return v[:, names.index(nm)]

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
    return up, np.array(ts), np.array(ms)

names, v = read_raw(TWELVE)
t = v[:, 0]
up, tms, mus = cycle_means(t, col_of(v, names, 'V(v1)'), col_of(v, names, 'V(v2)'))
per = np.diff(up)

print('=' * 100)
print('1. TRAP CHECK: the 5-cycle screen is a noisy, length-dependent estimator')
print('=' * 100)
print(f'  complete output cycles in the 12 ms tail: {len(per)}')
print(f'  period: mean={per.mean()*1e6:.6f} us  std={per.std()*1e9:.3f} ns')
print(f'  period span over ALL {len(per)} cycles = {np.ptp(per)/per.mean()*100:.6f} %')
print()
print(f'  {"n trailing cycles":>18s} {"period span (%)":>17s} {"V2 mean span (mV)":>19s}')
for n in [5, 10, 20, 50, 100, 500, 1000, 5000, len(per)]:
    if n > len(per):
        continue
    seg = per[-n:]
    mspan = np.ptp(mus[-n:]) * 1e3
    print(f'  {n:18d} {np.ptp(seg)/seg.mean()*100:17.6f} {mspan:19.6f}')

print()
print('=' * 100)
print('2. TRAP CHECK: is the last-5-cycle PASS a real settling or a short window?')
print('=' * 100)
print(f'  {"window":>16s} {"cycles":>8s} {"mean V2 (V)":>15s} {"span (mV)":>11s}')
edges = [11.5, 11.6, 11.7, 11.8, 11.9, 11.95, 12.0]
for lo, hi in zip(edges[:-1], edges[1:]):
    w = (tms >= lo * 1e-3) & (tms < hi * 1e-3)
    if w.sum() < 2:
        continue
    seg = mus[w]
    print(f'  {f"{lo:.2f}-{hi:.2f}":>16s} {int(w.sum()):8d} {seg.mean():15.9f} {np.ptp(seg)*1e3:11.6f}')

print()
print('=' * 100)
print('3. FULL-WINDOW TREND (not just the last five cycles)')
print('=' * 100)
A = np.vstack([tms, np.ones_like(tms)]).T
slope = np.linalg.lstsq(A, mus, rcond=None)[0][0]
# tms is in SECONDS and mus in VOLTS, so slope is V/s, which is numerically
# identical to mV/ms (1000 mV / 1000 ms). No scaling factor applies.
print(f'  linear fit over the whole 500 us tail: dV/dt = {slope:+.6f} mV/ms')
print(f'  span over ALL {len(mus)} cycles = {np.ptp(mus)*1e3:.6f} mV = {np.ptp(mus)/AMP*100:.6f} %')
print(f'  (only {len(mus)} complete cycles exist in a 500 us tail, so the')
print(f'   "last 100 / 1000 cycles" checks used on the 9 ms tail are N/A here)')

print()
print('=' * 100)
print('4. DRIFT-RATE DECAY: 9 ms -> 12 ms  (the decisive evidence)')
print('=' * 100)
n9, v9 = read_raw(NINE)
_, t9s, m9s = cycle_means(v9[:, 0], col_of(v9, n9, 'V(v1)'), col_of(v9, n9, 'V(v2)'))
with np.load(SEVEN, allow_pickle=True) as z:
    a7 = z['data']; n7 = z['names'].tolist()
_, t7s, m7s = cycle_means(a7[:, 0], col_of(a7, n7, 'V(v1)'), col_of(a7, n7, 'V(v2)'))

tl = np.concatenate([t7s, t9s, tms]) * 1e3
ml = np.concatenate([m7s, m9s, mus]) * 1e3

print(f'  {"window (ms)":>17s} {"rate (mV/ms)":>15s} {"decay vs prev":>15s}')
rates = []
for lo in np.arange(2.5, 12.0, 0.5):
    w = (tl >= lo) & (tl < lo + 0.5)
    if w.sum() < 3:
        continue
    r = float(np.polyfit(tl[w], ml[w], 1)[0])
    prev = rates[-1][1] if rates else None
    dec = f'{r/prev:.4f}' if prev else '-'
    print(f'  {f"{lo:.2f}-{lo+0.5:.2f}":>17s} {r:15.4f} {dec:>15s}')
    rates.append((lo + 0.25, r))

print()
print(f'  9 ms review reported: drift 11.9058 mV/ms at 8.5-9 ms, tau ~ 1.005 ms,')
print(f'                        gap -12.7150 mV, projected final -0.7446 mV (0.0155%)')

# Compare measured 12 ms against the 9 ms projection
NOMINAL = 4.496040582
w11 = tl >= 11.5
cur12 = float(ml[w11].mean())
gap12 = cur12 - NOMINAL * 1e3
print()
print(f'  MEASURED at 12 ms (full 11.5-12.0 ms window):')
print(f'    V2 time-weighted mean = {cur12:.6f} mV')
print(f'    accepted nominal      = {NOMINAL*1e3:.6f} mV')
print(f'    gap                   = {gap12:+.4f} mV = {gap12/AMP/10:+.4f} % of amplitude')

res = {
    'n_cycles': int(len(mus)),
    'period_span_all_pct': float(np.ptp(per)/per.mean()*100),
    'v2_mean_span_all_mV': float(np.ptp(mus)*1e3),
    'v2_mean_span_all_pct': float(np.ptp(mus)/AMP*100),
    'drift_whole_tail_mV_per_ms': float(slope),
    'V2_mean_11p5_12_mV': cur12,
    'gap_11p5_12_mV': float(gap12),
    'gap_11p5_12_pct': float(gap12/AMP/10),
    'rates': [[float(a), float(b)] for a, b in rates],
}
(OUT / 'cold12ms_verification.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "cold12ms_verification.json"}')
