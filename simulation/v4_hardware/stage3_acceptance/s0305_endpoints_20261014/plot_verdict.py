"""Plot the S03-05 seven-endpoint verdict with condition made explicit.

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
    rows = [r for r in verdict['cases']
            if r['precharged_5ms_tail'] or r['precharged_2ms_full']]

    labels, vin, vout, din, dout, settling, spans = [], [], [], [], [], [], []
    for r in rows:
        # Prefer the accepted 5 ms condition where it exists; else the 2 ms resupply.
        tail, full = r['precharged_5ms_tail'], r['precharged_2ms_full']
        d = tail or full
        labels.append(f"{r['case']}\n{r['target_vpp']}Vpp/{r['target_duty_percent']}%")
        vin.append(d['vin_vpp'])
        vout.append(d['vout_vpp'])
        din.append(d['din_percent'])
        dout.append(d['dout_percent'])
        settling.append(bool(full and not tail))       # only 2 ms data -> still settling
        spans.append(d['mean_span_percent'])

    x = np.arange(len(labels))
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.0), layout='constrained')

    colors = ['tab:orange' if s else 'tab:blue' for s in settling]
    ax[0].bar(x - .2, vin, .4, label='Vin measured', color='tab:blue')
    ax[0].bar(x + .2, vout, .4, label='Vout measured', color=colors)
    ax[0].plot(x, [r['target_vpp'] for r in rows], 'k_', markersize=22, label='Vin target')
    ax[0].set(title='Amplitude (orange = 2 ms window, still settling)', ylabel='Vpp (V)')
    ax[0].legend(fontsize=8)

    ax[1].bar(x - .2, din, .4, label='duty in')
    ax[1].bar(x + .2, dout, .4, label='duty out')
    ax[1].plot(x, [r['target_duty_percent'] for r in rows], 'k_', markersize=22, label='target')
    ax[1].set(title='Duty cycle (comparable across conditions)', ylabel='%')
    ax[1].legend(fontsize=8)

    ax[2].bar(x, spans, .55, color=colors)
    ax[2].axhline(0.1, color='r', ls='--', lw=1.4, label='frozen 0.1% screen')
    ax[2].set(title='Repeatability screen: mean span %', ylabel='%')
    ax[2].legend(fontsize=8)

    # Linearity uses only the same-condition accepted pair.
    lin = verdict.get('linearity')
    if lin:
        ax[2].annotate(
            f"linearity (5 ms, C4/C5):\n{lin['error_percent']:+.4f}%",
            xy=(0.02, 0.95), xycoords='axes fraction', va='top', fontsize=8,
            bbox=dict(boxstyle='round', fc='w', ec='0.7'))

    for a in ax:
        a.grid(alpha=.25)
        a.set_xticks(x)
        a.set_xticklabels(labels, fontsize=8)

    fig.suptitle('S03-05 key endpoints  (blue = accepted precharged 5 ms tail; '
                 'orange = resupply precharged 2 ms full window, not yet settled)', fontsize=10)
    fig.savefig(HERE / 'S03_05_verdict.png', dpi=160)
    print('wrote', HERE / 'S03_05_verdict.png')


if __name__ == '__main__':
    main()
