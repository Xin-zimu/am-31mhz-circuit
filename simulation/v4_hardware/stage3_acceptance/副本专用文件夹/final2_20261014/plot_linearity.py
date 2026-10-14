"""Read-only: 2 Vpp linearity plot + final report inputs."""
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
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

src = S / 'measure_stage3.py'
syn = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syn.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))


def measure(path):
    names, v = read_raw(path)
    t = v[:, 0]

    def col(nm):
        return v[:, names.index(nm)]

    uni = np.arange(t[-1] - 3e-4, t[-1], 2e-9)
    thr = np.mean(np.percentile(np.interp(uni, t, col('V(v1)')), [2, 98]))
    up, down = crossings(t, col('V(v1)'), thr)
    rows = []
    for a, b in list(zip(up[:-1], up[1:]))[-5:]:
        g = np.arange(a, b, 2e-9)
        falls = down[(down > a) & (down < b)]
        r = {'freq': 1 / (b - a),
             'duty': 100 * (falls[0] - a) / (b - a) if len(falls) == 1 else np.nan}
        for nm in ['V(v1)', 'V(v2)']:
            y = np.interp(g, t, col(nm))
            lo, hi = np.percentile(y, [2, 98])
            r[nm + '_vpp'] = float(hi - lo)
            r[nm + '_mean'] = float(np.trapezoid(y, g) / (g[-1] - g[0]))
        rows.append(r)
    return {
        'vin': float(np.mean([r['V(v1)_vpp'] for r in rows])),
        'vout': float(np.mean([r['V(v2)_vpp'] for r in rows])),
        'v2_mean': float(np.mean([r['V(v2)_mean'] for r in rows])),
        'freq': float(np.mean([r['freq'] for r in rows])),
        'duty': float(np.nanmean([r['duty'] for r in rows])),
        't': t, 'v1': col('V(v1)'), 'v2': col('V(v2)'),
    }


a4 = measure(RUN / 'REF_4Vpp_tail.raw')
a2 = measure(RUN / 'LIN_2Vpp_tail.raw')

g4, g2 = a4['vout'] / a4['vin'], a2['vout'] / a2['vin']
print(f'4 Vpp: Vin={a4["vin"]:.6f}  Vout={a4["vout"]:.6f}  gain={g4:.5f}')
print(f'2 Vpp: Vin={a2["vin"]:.6f}  Vout={a2["vout"]:.6f}  gain={g2:.5f}')
print(f'normalised gain at 2 Vpp = {g2/g4:.5f}  ({(g2/g4-1)*100:+.4f} %)')

# ---------------------------------------------------------------- plot
fig, axes = plt.subplots(2, 2, figsize=(14, 9))

ax = axes[0][0]
for lab, d, c in [('4 Vpp (REF)', a4, 'steelblue'), ('2 Vpp (LIN)', a2, 'darkorange')]:
    m = d['t'] >= d['t'][-1] - 120e-6
    ax.plot((d['t'][m] - d['t'][-1]) * 1e6, d['v2'][m], lw=0.9, color=c, label=lab)
ax.set_xlabel('time relative to 5 ms  [µs]')
ax.set_ylabel('V(v2)  [V]')
ax.set_title('Demodulated output, last 120 µs')
ax.legend(fontsize=9)
ax.grid(alpha=.3)

ax = axes[0][1]
for lab, d, c in [('4 Vpp (REF)', a4, 'steelblue'), ('2 Vpp (LIN)', a2, 'darkorange')]:
    m = d['t'] >= d['t'][-1] - 55e-6
    ax.plot((d['t'][m] - d['t'][-1]) * 1e6, d['v1'][m], lw=0.9, color=c, label=lab + ' input')
ax.set_xlabel('time relative to 5 ms  [µs]')
ax.set_ylabel('V(v1)  [V]')
ax.set_title('Input to the demodulator (attenuator output)')
ax.legend(fontsize=9)
ax.grid(alpha=.3)

ax = axes[1][0]
labels = ['4 Vpp\n(reference)', '2 Vpp\n(measured)']
vin = [a4['vin'], a2['vin']]
vout = [a4['vout'], a2['vout']]
x = np.arange(2)
ax.bar(x - 0.2, vin, 0.4, label='Vin (Vpp)', color='gray')
ax.bar(x + 0.2, vout, 0.4, label='Vout (Vpp)', color='seagreen')
for i, (a, b) in enumerate(zip(vin, vout)):
    ax.text(i - 0.2, a + .08, f'{a:.4f}', ha='center', fontsize=8)
    ax.text(i + 0.2, b + .08, f'{b:.4f}', ha='center', fontsize=8)
ax.axhline(a4['vout'] / 2, color='crimson', ls='--', lw=1.2,
           label=f'exact half of 4 Vpp = {a4["vout"]/2:.4f}')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel('amplitude  [Vpp]')
ax.set_title('Amplitude: 2 Vpp output is NOT exactly half')
ax.legend(fontsize=9)
ax.grid(alpha=.3, axis='y')

ax = axes[1][1]
ng = [1.0, g2 / g4]
bars = ax.bar(['4 Vpp', '2 Vpp'], ng, color=['steelblue', 'darkorange'], width=.55)
ax.axhline(1.0, color='gray', ls='-', lw=1)
ax.set_ylim(0.97, 1.005)
ax.set_ylabel('normalised gain  (4 Vpp = 1)')
ax.set_title(f'Normalised gain error at 2 Vpp = {(g2/g4-1)*100:+.4f} %')
for b, v in zip(bars, ng):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.0008, f'{v:.5f}', ha='center', fontsize=10)
ax.grid(alpha=.3, axis='y')

fig.tight_layout()
fig.savefig(OUT / 'linearity_2vpp.png', dpi=140)
print(f'plot: {OUT / "linearity_2vpp.png"}')

res = {
    'four_vpp': {k: a4[k] for k in ('vin', 'vout', 'v2_mean', 'freq', 'duty')},
    'two_vpp': {k: a2[k] for k in ('vin', 'vout', 'v2_mean', 'freq', 'duty')},
    'gain_4': g4, 'gain_2': g2, 'norm_gain_2': g2 / g4,
    'linearity_error_percent': (g2 / g4 - 1) * 100,
    'exact_half_expected_vout': a4['vout'] / 2,
    'deviation_from_half_mV': (a2['vout'] - a4['vout'] / 2) * 1e3,
    'definition': 'linearity error = (normalised gain at 2 Vpp / gain at 4 Vpp) - 1',
}
json.dump(res, (OUT / 'linearity_final.json').open('w', encoding='utf-8'),
          ensure_ascii=False, indent=2, default=float)
print()
print(json.dumps(res, ensure_ascii=False, indent=2, default=float))
