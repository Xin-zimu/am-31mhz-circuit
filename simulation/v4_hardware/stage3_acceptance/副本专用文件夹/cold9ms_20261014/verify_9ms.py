"""Read-only: verify the 9 ms result and diagnose the period-span anomaly.

Two things to check before trusting the PASS:
  1. Does the period relative span (0.00509%) exceed the 0.1% screen on its own?
     It does not -- but it grew 2.6x versus 7 ms, so explain why.
  2. Is the trend genuinely settling, or is 5 cycles too short a window?

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

NINE = RUN / 'COLD_9ms_tail.raw'
names, v = read_raw(NINE)
t = v[:, 0]

def col(nm):
    return v[:, names.index(nm)]

print('=' * 100)
print('1. THE PERIOD-SPAN QUESTION')
print('=' * 100)
# Find EVERY complete output cycle in the 500 us window, not just the last 5.
win = t >= t[-1] - 3e-4
uniform = np.arange(t[win][0], t[-1], 2e-9)
vin = np.interp(uniform, t, col('V(v1)'))
thr = np.mean(np.percentile(vin, [2, 98]))
up, down = crossings(t, col('V(v1)'), thr)
per = np.diff(up)
print(f'  complete output cycles found in the last 300 us: {len(per)}')
print(f'  period: mean={per.mean()*1e6:.6f} us  std={per.std()*1e9:.3f} ns  '
      f'min={per.min()*1e6:.6f}  max={per.max()*1e6:.6f}')
print(f'  period span over ALL {len(per)} cycles = {np.ptp(per)/per.mean()*100:.6f} %')
print()
print(f'  the SAME span measured over different numbers of trailing cycles:')
print(f'  {"n trailing cycles":>18s} {"span (%)":>12s} {"V2 mean span (mV)":>19s}')
for n in [5, 10, 20, 50, 100, 500, 1000, 2000, len(per)]:
    if n > len(per):
        continue
    seg = per[-n:]
    span = np.ptp(seg) / seg.mean() * 100
    # V2 mean per cycle in that segment
    mus = []
    for k in range(len(up) - n - 1, len(up) - 1):
        a, b = up[k], up[k + 1]
        g = np.arange(a, b, 2e-9)
        yy = np.interp(g, t, col('V(v2)'))
        mus.append(np.trapezoid(yy, g) / (g[-1] - g[0]))
    mspan = (max(mus) - min(mus)) * 1e3
    print(f'  {n:18d} {span:12.6f} {mspan:19.6f}')
print()
print('  => the 5-cycle window is a NOISY estimator. Its period span is dominated by')
print('     the sampling grid, not by physical drift. Check the trend instead.')

print()
print('=' * 100)
print('2. THE TREND: V(v2) cycle mean over the whole 500 us window')
print('=' * 100)
mus, tms = [], []
for k in range(len(up) - 1):
    a, b = up[k], up[k + 1]
    g = np.arange(a, b, 2e-9)
    yy = np.interp(g, t, col('V(v2)'))
    mus.append(np.trapezoid(yy, g) / (g[-1] - g[0]))
    tms.append((a + b) / 2)
mus = np.array(mus)
tms = np.array(tms)
print(f'  cycles analysed: {len(mus)}  from {tms[0]*1e3:.6f} to {tms[-1]*1e3:.6f} ms')
print()
print(f'  {"window (ms)":>20s} {"cycles":>8s} {"mean V2 (V)":>15s} {"min":>13s} {"max":>13s} {"span (mV)":>11s}')
edges = [8.5, 8.55, 8.6, 8.7, 8.8, 8.9, 8.95, 9.0]
for lo, hi in zip(edges[:-1], edges[1:]):
    w = (tms >= lo * 1e-3) & (tms < hi * 1e-3)
    if w.sum() < 2:
        continue
    seg = mus[w]
    print(f'  {f"{lo:.2f}-{hi:.2f}":>20s} {int(w.sum()):8d} {seg.mean():15.9f} '
          f'{seg.min():13.9f} {seg.max():13.9f} {np.ptp(seg)*1e3:11.6f}')

# linear drift of the cycle mean over time
A = np.vstack([tms, np.ones_like(tms)]).T
slope, intercept = np.linalg.lstsq(A, mus, rcond=None)[0]
print()
print(f'  linear fit over the whole window: dV/dt = {slope*1e3:+.6f} mV/ms')
print(f'    => projected drift over a further 1 ms: {slope*1e-3*1e3:+.6f} mV')
print(f'    => projected drift over a further 10 ms: {slope*1e-3*10e3:+.6f} mV')
print(f'  (as a fraction of amplitude 4.816 V: {abs(slope)*1e-3*10e3/4.816*100:.6f} % over 10 ms)')

print()
print('=' * 100)
print('3. FULL-WINDOW V2 MEAN SPAN (all cycles, not just the last five)')
print('=' * 100)
amp = 4.816122
print(f'  span over ALL {len(mus)} cycles = {np.ptp(mus)*1e3:.6f} mV '
      f'= {np.ptp(mus)/amp*100:.6f} % of amplitude')
print(f'  span over the last 100 cycles = {np.ptp(mus[-100:])*1e3:.6f} mV '
      f'= {np.ptp(mus[-100:])/amp*100:.6f} %')
print(f'  span over the last 1000 cycles = {np.ptp(mus[-1000:])*1e3:.6f} mV '
      f'= {np.ptp(mus[-1000:])/amp*100:.6f} %')
print(f'  first 100 cycles mean = {mus[:100].mean():.9f} V')
print(f'  last 100 cycles mean  = {mus[-100:].mean():.9f} V')
print(f'  difference            = {(mus[-100:].mean()-mus[:100].mean())*1e3:+.6f} mV')

res = {
    'n_cycles': int(len(mus)),
    'period_span_all_pct': float(np.ptp(per) / per.mean() * 100),
    'v2_mean_span_all_mV': float(np.ptp(mus) * 1e3),
    'v2_mean_span_all_pct': float(np.ptp(mus) / amp * 100),
    'drift_mV_per_ms': float(slope * 1e3),
    'first100_mean_V': float(mus[:100].mean()),
    'last100_mean_V': float(mus[-100:].mean()),
    'amp_V': amp,
}
(OUT / 'cold9ms_verification.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "cold9ms_verification.json"}')
