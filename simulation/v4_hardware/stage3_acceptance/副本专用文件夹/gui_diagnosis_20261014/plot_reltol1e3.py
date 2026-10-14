"""Read-only: visualise the RELTOL=1e-3 GUI success against the failure.

No simulator calls.
"""
from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
E = K / 'gui_evidence_20261014'
STG = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

F0 = 31e6
PERIOD = 1 / F0
EVENT = 7 * PERIOD


def traces(path):
    root = ET.parse(path).getroot()
    out = {}
    for tr in root.iter('CTrace'):
        d = tr.find('Data')
        if d is None:
            continue
        out[tr.get('Name').removeprefix('&ASC')] = (
            np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8'),
            np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8'))
    return out


new = traces(E / 'S03_GUI_COLD_20us_reltol1e3.xml')
old = traces(E / 'S03_GUI_COLD_20us_gra.xml')
nt = new['V(v1)'][0]
ot = old['V(v1)'][0]
ndt = np.diff(nt)
odt = np.diff(ot)

names, v = read_raw(STG / 'cold_engine_gui_net.raw')
et = v[:, 0]

fig, axes = plt.subplots(3, 1, figsize=(13.5, 11.5))

# ---- panel 1: the whole 20 us, new run
ax = axes[0]
ax.plot(nt * 1e6, new['V(v2)'][1], lw=0.8, color='seagreen',
        label='GUI RELTOL=1e-3, V(v2) — COMPLETED 20 µs')
ax.axvline(ot[-1] * 1e6, color='crimson', lw=1.3, ls=':',
           label=f'old run died here = {ot[-1]*1e9:.1f} ns')
ax.set_xlabel('time  [µs]')
ax.set_ylabel('V(v2)  [V]')
ax.set_title('Same project, one changed setting: RELTOL 1e-4 → 1e-3')
ax.legend(fontsize=9, loc='best')
ax.grid(alpha=.3)

# ---- panel 2: step size over the first microsecond
ax = axes[1]
m = nt[1:] <= 1e-6
mo = ot[1:] <= 1e-6
ax.semilogy(nt[1:][m] * 1e9, ndt[m] * 1e12, lw=1.0, color='seagreen',
            label='GUI 1e-3 step')
ax.semilogy(ot[1:][mo] * 1e9, odt[mo] * 1e12, lw=1.0, ls='--', color='darkorange',
            label='GUI 1e-4 step (the failing setting)')
ax.axvline(EVENT * 1e9, color='crimson', lw=1.2, ls=':',
           label=f'7 carrier periods = {EVENT*1e9:.3f} ns')
ax.axhline(1000, color='gray', lw=.9, ls='-.', label='requested cap = 1 ns')
ax.set_xlabel('time  [ns]')
ax.set_ylabel('accepted step  [ps]')
ax.set_title('RELTOL=1e-3 holds the step at the 1 ns cap; 1e-4 collapses at the event')
ax.legend(fontsize=8, loc='lower left')
ax.grid(alpha=.3, which='both')

# ---- panel 3: end game of the old run
ax = axes[2]
ax.semilogy(ot[1:] * 1e9, odt * 1e12, lw=1.2, color='darkorange')
ax.axvline(EVENT * 1e9, color='crimson', lw=1.3, ls=':',
           label=f'event = {EVENT*1e9:.3f} ns')
ax.set_xlim(224.5, 226.0)
ax.set_xlabel('time  [ns]')
ax.set_ylabel('GUI 1e-4 step  [ps]')
ax.set_title('Why the old run aborted: step ground down to 0.012 ps in the last 15 ps')
ax.legend(fontsize=9)
ax.grid(alpha=.3, which='both')
ax.annotate('ABORT', xy=(ot[-1] * 1e9, odt[-1] * 1e12),
            xytext=(-90, 40), textcoords='offset points',
            arrowprops=dict(arrowstyle='->', color='crimson'), color='crimson',
            fontsize=11, fontweight='bold')

fig.tight_layout()
fig.savefig(OUT / 'gui_reltol1e3_success.png', dpi=140)
print(f'plot: {OUT / "gui_reltol1e3_success.png"}')

# ---- numeric summary for the report
summary = {
    'old_reltol_1e-4': {
        'points': int(len(ot)), 'end_s': float(ot[-1]),
        'end_over_periods': float(ot[-1] / PERIOD),
        'median_step_s': float(np.median(odt)),
        'pct_at_cap': float(100 * (odt > 0.999e-9).mean()),
        'deepest_step_at_event_s': float(odt[np.abs(ot[1:] - EVENT) < 3e-9].min()),
        'outcome': 'ABORTED',
    },
    'new_reltol_1e-3': {
        'points': int(len(nt)), 'end_s': float(nt[-1]),
        'end_over_periods': float(nt[-1] / PERIOD),
        'median_step_s': float(np.median(ndt)),
        'pct_at_cap': float(100 * (ndt > 0.999e-9).mean()),
        'deepest_step_at_event_s': float(ndt[np.abs(nt[1:] - EVENT) < 3e-9].min()),
        'outcome': 'COMPLETED',
    },
    'engine_same_netlist': {
        'points': int(len(et)),
        'median_step_s': float(np.median(np.diff(et))),
        'pct_at_cap': float(100 * (np.diff(et) > 0.999e-9).mean()),
        'deepest_step_at_event_s': float(np.diff(et)[np.abs(et[1:] - EVENT) < 3e-9].min()),
    },
}
(OUT / 'gui_reltol1e3_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(json.dumps(summary, ensure_ascii=False, indent=2))
