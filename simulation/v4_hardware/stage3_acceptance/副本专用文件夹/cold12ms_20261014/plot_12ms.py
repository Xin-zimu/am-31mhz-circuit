"""Read-only: settling plot 7 -> 12 ms, same style as cold9ms_settling.png."""
from pathlib import Path
import sys
import ast
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
n9, v9 = read_raw(Path(r'D:\ms_xsp\stage3_acceptance\s0304_cold9ms_20261014') / 'COLD_9ms_tail.raw')
t9, m9 = cycle_means(v9[:, 0], v9[:, n9.index('V(v1)')], v9[:, n9.index('V(v2)')])
n12, v12 = read_raw(RUN / 'COLD_12ms_clean.raw')
t12, m12 = cycle_means(v12[:, 0], v12[:, n12.index('V(v1)')], v12[:, n12.index('V(v2)')])

tl = np.concatenate([t7, t9, t12]) * 1e3
ml = np.concatenate([m7, m9, m12]) * 1e3

fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))

ax[0].plot(tl, ml, lw=0.8, color='C0')
ax[0].axhline(NOMINAL * 1e3, color='k', ls='--', lw=1, label=f'accepted nominal {NOMINAL*1e3:.3f} mV')
ax[0].axvline(9.0, color='C1', ls=':', lw=1)
ax[0].axvline(11.5, color='C3', ls=':', lw=1)
ax[0].set_xlabel('t (ms)'); ax[0].set_ylabel('V(v2) cycle mean (mV)')
ax[0].set_title('Cold-start settling 7 -> 12 ms')
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

# drift rate
centres, rates = [], []
for lo in np.arange(2.5, 12.0, 0.5):
    w = (tl >= lo) & (tl < lo + 0.5)
    if w.sum() < 3:
        continue
    centres.append(lo + 0.25)
    rates.append(float(np.polyfit(tl[w], ml[w], 1)[0]))
ax[1].semilogy(centres, rates, 'o-', color='C2')
ax[1].set_xlabel('t (ms)'); ax[1].set_ylabel('drift rate (mV/ms)')
ax[1].set_title('Drift-rate decay (log scale)')
ax[1].grid(alpha=0.3, which='both')

fig.tight_layout()
fig.savefig(OUT / 'cold12ms_settling.png', dpi=130)
print(f'written: {OUT / "cold12ms_settling.png"}')
