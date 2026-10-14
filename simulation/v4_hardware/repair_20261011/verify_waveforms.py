"""Audit Multisim Grapher doubles and the controlled XSPICE A/B experiment."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
root = ET.parse(HERE / 'verified_gra.xml')
traces = {}
metrics = {'source': 'Multisim 14.3 GUI .gra; little-endian IEEE-754 doubles',
           'measurement_window_s': [0.0001, 0.0002], 'traces': {}}
for trace in root.findall('.//CTrace'):
    name = trace.get('Name').removeprefix('&ASC')
    d = trace.find('Data')
    x = np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8')
    y = np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8')
    assert len(x) == len(y) and np.all(np.isfinite(y))
    assert np.all(np.diff(x) >= 0) and abs(x[-1] - 0.0002) < 1e-12
    traces[name] = (x, y)
    keep = x >= 0.0001
    metrics['traces'][name] = {'points': len(x), 't_end_s': float(x[-1]),
                              'min_V': float(y[keep].min()),
                              'max_V': float(y[keep].max()),
                              'time_weighted_mean_V': float(np.trapezoid(y[keep], x[keep]) / (x[keep][-1] - x[keep][0]))}

ab = {}
for label in ['open', 'connected']:
    z = np.load(HERE / f'{label}_output.npz')
    names, a = list(z['names']), z['data']
    ab[label] = (names, a)
    i = names.index('V(bbo)')
    y = a[a[:, 0] >= 0.0001, i]
    metrics[label + '_control_BBO_V'] = [float(y.min()), float(y.max())]

x = traces['V(bb_in)'][0]

plt.rcParams.update({'font.family': 'Microsoft YaHei', 'axes.unicode_minus': False,
                     'font.size': 10})
fig, axes = plt.subplots(3, 1, figsize=(11.8, 8), sharex=True,
                         gridspec_kw={'height_ratios': [1, 1.3, 1.5]}, layout='constrained')
for name, color in [('V(bb_in)', '#007c91'), ('V(bb_fb)', '#d97706')]:
    tx, yy = traces[name]
    axes[0].plot(tx[::20]*1e6, yy[::20], label=name, lw=1, color=color)
axes[0].set_ylim(4.2, 4.8)
axes[0].set_title('修复后：运放输入与反馈（Multisim 界面运行结果）', loc='left')
for name, color in [('V(bbo)', '#185adb'), ('V(v2)', '#d97706')]:
    tx, yy = traces[name]
    axes[1].plot(tx[::20]*1e6, yy[::20], label=name, lw=1.2, color=color)
axes[1].set_ylim(0, 9)
axes[1].set_title('修复后：运放输出 BBO 与最终输出 V2', loc='left')
for label, color, legend in [('open', '#b94141', '原连接：BBO ≈ 3.868 V'),
                             ('connected', '#185adb', '只修复输出连接')]:
    names, a = ab[label]
    axes[2].plot(a[::20, 0]*1e6, a[::20, names.index('V(bbo)')],
                 label=legend, lw=1.2, color=color)
axes[2].set_title('单变量对照：同一 OPAx197 模型、相同初值（Multisim XSPICE）', loc='left')
axes[2].set_ylim(0, 9)
for ax in axes:
    ax.set_xlim(0, 200)
    ax.set_ylabel('电压 / V')
    ax.grid(alpha=.2)
    ax.legend(loc='upper right', ncol=2, fontsize=9)
axes[-1].set_xlabel('时间 / μs')
fig.suptitle('OPA197 输出悬空修复验证 · 200 μs', fontsize=17, fontweight='bold')
fig.savefig(HERE.parent / 'AM_20k_31MHz_V4_3_VERIFIED.png', dpi=170)
(HERE / 'verified_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
np.savez_compressed(HERE / 'verified_gra.npz', time=x,
                    **{name: values[1] for name, values in traces.items()})
print(json.dumps(metrics, ensure_ascii=False, indent=2))
