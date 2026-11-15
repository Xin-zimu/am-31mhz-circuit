"""Figures for the Stage AM-AD835.1 report, all from stored JSON results."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rf_study as L

ROOT = L.ROOT
RES = ROOT / 'results'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
C1, C2, C3 = '#2469ad', '#b03528', '#1d6f42'

LOAD = [('load_500_4p', 500), ('load_600_4p', 600), ('load_700_4p', 700),
        ('load_800_4p', 800), ('load_900_4p', 900), ('load_1k_4p', 1000),
        ('load_2k_4p', 2000), ('load_3k3_4p', 3300), ('load_10k_4p', 10000),
        ('load_37k5_4p', 37500), ('load_50k_4p', 50000), ('load_100k_4p', 100000)]


def get(n):
    p = RES / f'{n}.json'
    return json.loads(p.read_text(encoding='utf8')) if p.exists() else None


def peak(v):
    return max(abs(v['min']), abs(v['max']))


fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))

# ---- panel 1: TP2 amplitude and Y peak versus external load (all 4 pF) ------
R, V, P = [], [], []
for n, r in LOAD:
    j = get(n)
    if j:
        R.append(r); V.append(j['out']['vpp']); P.append(peak(j['y']))
ax[0].semilogx(R, V, 'o-', color=C1, label='TP2 Vpp')
ax[0].semilogx(R, P, 's--', color=C2, label='|Y peak| (RC fixture)')
ax[0].axhline(1.0, color='k', ls=':', lw=1.2, label='±1 V nominal')
ax[0].axhline(1.995, color=C3, ls=':', lw=1.2, label='2.0 Vpp target')
j = get('load_2k_10p')
ax[0].plot([2000], [j['out']['vpp']], 'D', ms=8, mfc='none', mec=C3, mew=2,
           label='2 kΩ∥10 pF (original C4)')
ax[0].set_xlabel('external load resistance (Ω), 4 pF unless noted')
ax[0].set_ylabel('V')
ax[0].set_title('C4 TP2 vs external load')
ax[0].legend(fontsize=7.5, loc='upper left')
ax[0].grid(alpha=.3, which='both')

# ---- panel 2: scheme-A attenuator sizing -----------------------------------
SIZ = [('SA_330_620', 330, 620), ('SA_390_620', 390, 620), ('SA_390_680', 390, 680),
       ('SA_430_680', 430, 680), ('A470_nom', 470, 680), ('SA_470_620', 470, 620),
       ('SA_510_680', 510, 680), ('SA_560_680', 560, 680), ('A_nom', 330, 680)]
xs, ys, ns = [], [], []
for n, rs, rp in SIZ:
    j = get(n)
    if j:
        xs.append(rs); ys.append(peak(j['y'])); ns.append(f'{rs}/{rp}')
ax[1].scatter(xs, ys, c=C1, s=55, zorder=3)
for x, y, t in zip(xs, ys, ns):
    dy = -14 if t in ('330/680', '390/680') else 9
    ax[1].annotate(t, (x, y), textcoords='offset points', xytext=(0, dy),
                   ha='center', fontsize=7.5)
ax[1].set_ylim(min(ys) - 0.012, max(ys) + 0.016)
ax[1].axhline(1.0, color='k', ls=':', lw=1.2)
ax[1].axhspan(0.99, 1.01, color=C2, alpha=.18)
ax[1].set_xlabel('series resistor RS (Ω), shunt 620/680 Ω')
ax[1].set_ylabel('|Y peak| (V)')
ax[1].set_title('Scheme A attenuator sizing\n(need ≈0.99 V for 2.0/1.2 Vpp)')
ax[1].grid(alpha=.3)

# ---- panel 3: ideal-multiplier envelope on measured waveforms --------------
ar = json.loads((RES / 'envelope_arithmetic.json').read_text(encoding='utf8'))
lab, wh, wl = [], [], []
for e in ar:
    if e['convention'] != 'A':
        continue
    lab.append(f"{e['label']}"); wh.append(e['W_high_vpp']); wl.append(e['W_low_vpp'])
y = np.arange(len(lab))
ax[2].barh(y + .2, wh, .38, color=C1, label='W high envelope')
ax[2].barh(y - .2, wl, .38, color=C2, label='W low envelope')
ax[2].axvline(2.0, color=C3, ls='--', lw=1.4, label='2.0 Vpp target')
ax[2].axvline(1.2, color=C3, ls=':', lw=1.4, label='1.2 Vpp target')
ax[2].set_yticks(y); ax[2].set_yticklabels(lab, fontsize=7.5)
ax[2].set_xlabel('Vpp (ideal W = XY/U + Z)')
ax[2].set_title('Ideal envelope, scheme-A convention\n(NOT an AD835 simulation)')
ax[2].legend(fontsize=7.5); ax[2].grid(alpha=.3, axis='x')
ax[2].invert_yaxis()

plt.tight_layout()
plt.savefig(RES / 'fig_stage_am_ad835_1.png', dpi=130)
print('saved fig_stage_am_ad835_1.png')
for a in ax:
    print(a.get_title().split('\n')[0])
