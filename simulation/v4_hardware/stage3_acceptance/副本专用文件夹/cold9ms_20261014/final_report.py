"""Read-only: final consolidated cold-start settling report + plot.

Uses LOCAL decay constants (the settling is multi-exponential, so a single
global fit is not appropriate) and states the projection honestly.

No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
SCREEN_MV = 0.001 * AMP * 1e3


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

# ---- local tau from consecutive 0.5 ms windows -------------------------
wins = []
for lo in np.arange(2.5, 9.0, 0.5):
    w = (tl >= lo) & (tl < lo + 0.5)
    if w.sum() < 3:
        continue
    wins.append({'mid': lo + 0.25,
                 'rate': float(np.polyfit(tl[w], ml[w], 1)[0]),
                 'mean': float(ml[w].mean())})
# local tau between consecutive windows
for i in range(1, len(wins)):
    if wins[i]['rate'] > 0 and wins[i - 1]['rate'] > 0:
        dt = wins[i]['mid'] - wins[i - 1]['mid']
        wins[i]['tau_local'] = dt / np.log(wins[i - 1]['rate'] / wins[i]['rate'])

late = [w for w in wins if 'tau_local' in w and w['mid'] >= 7.0]
tau_late = float(np.mean([w['tau_local'] for w in late]))
r_late = [w for w in wins if w['mid'] >= 7.0]
d9 = float(np.mean([w['rate'] for w in r_late]))
gap = ml[tl >= 8.5].mean() - NOMINAL * 1e3
resid = d9 * tau_late

print('=' * 100)
print('LOCAL DECAY CONSTANT  (multi-exponential settling)')
print('=' * 100)
print(f'  {"window mid (ms)":>16s} {"rate (mV/ms)":>14s} {"local tau (ms)":>16s}')
for w in wins:
    tl_s = f'{w["tau_local"]:.4f}' if 'tau_local' in w else '--'
    print(f'  {w["mid"]:16.2f} {w["rate"]:14.4f} {tl_s:>16s}')
print()
print(f'  late-region (>=7 ms) mean rate   = {d9:.4f} mV/ms')
print(f'  late-region mean local tau       = {tau_late:.4f} ms')
print()
print(f'  NOTE: a single global exponential does NOT fit (RMS ~79 mV, and it')
print(f'  predicts an asymptote of 4.635 V, above the 4.496 V nominal).')
print(f'  The settling is multi-exponential; only the LOCAL behaviour is')
print(f'  well constrained, which is what the projection below uses.')

print()
print('=' * 100)
print('PROJECTION')
print('=' * 100)
print(f'  amplitude                          = {AMP:.6f} V')
print(f'  0.1% screen threshold              = {SCREEN_MV:.4f} mV')
print(f'  accepted pre-charged nominal       = {NOMINAL*1e3:.4f} mV')
print(f'  cold-start V2 mean at 9 ms         = {ml[tl>=8.5].mean():.4f} mV')
print(f'  gap now                            = {gap:+.4f} mV ({gap/AMP/10:+.4f} %)')
print(f'  remaining rise (rate x tau)        = {resid:+.4f} mV')
print(f'  projected final gap                = {gap+resid:+.4f} mV '
      f'({(gap+resid)/AMP/10:+.4f} %)')
print(f'  vs screen                          = '
      f'{"PASS" if abs(gap+resid) < SCREEN_MV else "FAIL"}')
print()
print(f'  sensitivity to tau:')
print(f'  {"tau (ms)":>10s} {"final gap (mV)":>16s} {"% of ampl":>11s} {"screen":>8s}')
for tt in [0.8, 1.0, tau_late, 1.2, 1.5, 2.0]:
    fg = gap + d9 * tt
    print(f'  {tt:10.4f} {fg:16.4f} {fg/AMP/10:11.4f} '
          f'{"PASS" if abs(fg) < SCREEN_MV else "FAIL":>8s}')

# ------------------------------------------------------------------ plot
fig, axes = plt.subplots(2, 1, figsize=(13, 9.5))

ax = axes[0]
ax.plot(tl, ml, 'o-', ms=3.2, lw=1.1, color='steelblue')
ax.axhline(NOMINAL * 1e3, color='crimson', lw=1.3, ls='--',
           label=f'accepted pre-charged nominal = {NOMINAL*1e3:.1f} mV')
ax.axhline(NOMINAL * 1e3 + SCREEN_MV, color='gray', lw=.9, ls=':')
ax.axhline(NOMINAL * 1e3 - SCREEN_MV, color='gray', lw=.9, ls=':',
           label=f'±0.1% screen = ±{SCREEN_MV:.2f} mV')
ax.axvline(7.0, color='seagreen', lw=1.0, ls='-.', label='7 ms (previous limit)')
ax.plot([9.0], [ml[tl >= 8.5].mean()], 'k*', ms=14,
        label='9 ms measurement')
ax.errorbar([9.0 + tau_late], [ml[tl >= 8.5].mean() + resid], yerr=SCREEN_MV,
            fmt='D', color='darkorange', ms=7, capsize=4,
            label=f'projected asymptote (+{tau_late:.2f} ms)')
ax.set_xlabel('time  [ms]')
ax.set_ylabel('V(v2) cycle mean  [mV]')
ax.set_title('Cold-start bias settling: still rising at 9 ms, decaying with tau ~ %.2f ms'
             % tau_late)
ax.legend(fontsize=8.5, loc='lower right')
ax.grid(alpha=.3)
ax.set_xlim(0, 11.5)

ax = axes[1]
mids = [w['mid'] for w in wins]
rates = [w['rate'] for w in wins]
ax.semilogy(mids, rates, 's-', color='darkorange', ms=5, lw=1.2)
ax.set_xlabel('time  [ms]')
ax.set_ylabel('bias drift rate  [mV/ms]')
ax.set_title('Drift rate decays steadily -- a genuine settling tail')
ax.grid(alpha=.3, which='both')
for w in wins:
    if 'tau_local' in w and w['mid'] >= 7.0:
        ax.annotate(f'τ={w["tau_local"]:.2f} ms', xy=(w['mid'], w['rate']),
                    xytext=(8, 12), textcoords='offset points', fontsize=8)
ax.axvline(7.0, color='seagreen', lw=1.0, ls='-.')

fig.tight_layout()
fig.savefig(OUT / 'cold9ms_settling.png', dpi=140)
print()
print(f'plot: {OUT / "cold9ms_settling.png"}')

json.dump({'wins': wins, 'tau_late_ms': tau_late, 'rate_9ms': d9,
           'gap_mV': float(gap), 'residual_mV': float(resid),
           'projected_final_gap_mV': float(gap + resid),
           'screen_mV': float(SCREEN_MV), 'amplitude_V': AMP,
           'nominal_mV': NOMINAL * 1e3},
          (OUT / 'cold9ms_final.json').open('w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print(f'written: {OUT / "cold9ms_final.json"}')
