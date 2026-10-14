"""Plot the S03-05 seven-endpoint verdict: measured input/output amplitudes and duties.

Run: python -X utf8 plot_verdict.py
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def main():
    verdict = json.loads((HERE / 'verdict_table.json').read_text(encoding='utf-8'))
    rows = [r for r in verdict['cases'] if r['precharged'] or r['fullwindow']]

    labels, vin, vout, din, dout, conds = [], [], [], [], [], []
    for r in rows:
        d = r['precharged'] or r['fullwindow']
        labels.append(f"{r['case']}\n{r['target_vpp']}Vpp/{r['target_duty_percent']}%")
        vin.append(d['vin_vpp'])
        vout.append(d['vout_vpp'])
        din.append(d['din_percent'])
        dout.append(d['dout_percent'])
        conds.append('P' if r['precharged'] else 'C')

    x = np.arange(len(labels))
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), layout='constrained')

    ax[0].bar(x - .2, vin, .4, label='Vin measured')
    ax[0].bar(x + .2, vout, .4, label='Vout measured')
    ax[0].plot(x, [r['target_vpp'] for r in rows], 'k_', markersize=22, label='Vin target')
    ax[0].set(title='Amplitude: measured vs target', ylabel='Vpp (V)')
    ax[0].legend(fontsize=8)

    ax[1].bar(x - .2, din, .4, label='duty in')
    ax[1].bar(x + .2, dout, .4, label='duty out')
    ax[1].plot(x, [r['target_duty_percent'] for r in rows], 'k_', markersize=22, label='target')
    ax[1].set(title='Duty cycle', ylabel='%')
    ax[1].legend(fontsize=8)

    # Linearity: v2 vs v1 for the accepted precharged chain (C4 4 Vpp, C5 2 Vpp).
    lin = verdict.get('linearity')
    if lin:
        v1 = np.array([lin['v1_2vpp'], lin['v1_4vpp']])
        v2 = np.array([lin['v2_2vpp'], lin['v2_4vpp']])
        ax[2].plot(v1, v2, 'o-', label='measured')
        ideal = v2[1] / v1[1] * v1
        ax[2].plot(v1, ideal, 'k--', label='ideal linear through 4 Vpp')
        for xi, yi, name in zip(v1, v2, ['C5 2Vpp', 'C4 4Vpp']):
            ax[2].annotate(name, (xi, yi), textcoords='offset points', xytext=(6, -12), fontsize=8)
        ax[2].set(title=f"Linearity (precharged): error {lin['error_percent']:+.4f}%",
                  xlabel='v1 Vpp (V)', ylabel='v2 Vpp (V)')
        ax[2].legend(fontsize=8)

    for a in ax[:2]:
        a.grid(alpha=.25)
        a.set_xticks(x)
        a.set_xticklabels(labels, fontsize=8)
    ax[2].grid(alpha=.25)
    ax[2].set_xticks(np.arange(0, 5, 1))
    ax[2].set_xlim(0, 5)

    fig.suptitle('S03-05 key endpoints  (P = precharged 5 ms tail, C = cold-start full window 2 ms)',
                 fontsize=11)
    fig.savefig(HERE / 'S03_05_verdict.png', dpi=160)
    print('wrote', HERE / 'S03_05_verdict.png')


if __name__ == '__main__':
    main()
