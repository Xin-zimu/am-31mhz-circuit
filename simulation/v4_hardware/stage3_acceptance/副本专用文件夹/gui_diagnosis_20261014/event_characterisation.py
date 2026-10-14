"""Read-only: characterise the startup event at 7 carrier periods, and plot it.

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
CAP = PERIOD / 32
labels = ['V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)']

names, v = read_raw(STG / 'cold_engine_gui_net.raw')
t = v[:, 0]

print('=' * 96)
print('1. STARTUP TRAJECTORY (engine, cold start from zero IC)')
print('=' * 96)
print(f'  {"t (ns)":>10s} {"dt (ps)":>9s} ' + ' '.join(f'{l:>13s}' for l in labels))
for tk in [0, 1e-11, 2e-11, 5e-11, 1e-10, 2e-10, 5e-10, 1e-9, 2e-9, 5e-9, 1e-8,
           2e-8, 5e-8, 1e-7, 1.5e-7, 2e-7, 2.2e-7, EVENT, 2.4e-7, 3e-7, 5e-7, 1e-6]:
    j = int(np.searchsorted(t, tk))
    if j <= 0 or j >= len(t):
        continue
    dtp = (t[j] - t[j-1]) * 1e12
    print(f'  {t[j]*1e9:10.5f} {dtp:9.3f} ' +
          ' '.join(f'{v[j, i+1]:13.8f}' for i in range(4)))

print()
print('=' * 96)
print('2. WHAT IS MOVING FAST AT THE EVENT?  (max |dV/dt| per node, 1 ns window)')
print('=' * 96)
for lo_ns, hi_ns in [(200, 225), (225, 226), (226, 250), (250, 300)]:
    m = (t >= lo_ns * 1e-9) & (t < hi_ns * 1e-9)
    if m.sum() < 3:
        continue
    row = []
    for i, lab in enumerate(labels, start=1):
        col = v[m, i]
        tt = t[m]
        d = np.abs(np.diff(col) / np.diff(tt))
        row.append(f'{lab}={d.max():.3e}')
    print(f'  {lo_ns:4d}-{hi_ns:4d} ns : ' + '  '.join(row))

print()
print('=' * 96)
print('3. CARRIER-RATE RIPPLE AMPLITUDE (V(bbo)) -- does it peak near the event?')
print('=' * 96)
m = t < 400e-9
tt, bbo = t[m], v[m, 2]
print(f'  {"window (ns)":>16s} {"V(bbo) pp":>12s} {"V(bbo) mean":>13s}')
for lo, hi in [(0, 32.26), (32.26, 64.52), (64.52, 96.77), (96.77, 129.03),
               (129.03, 161.29), (161.29, 193.55), (193.55, 225.81),
               (225.81, 258.06), (258.06, 290.32), (290.32, 322.58),
               (322.58, 354.84), (354.84, 387.10)]:
    w = (tt >= lo * 1e-9) & (tt < hi * 1e-9)
    if w.sum() < 3:
        continue
    print(f'  {f"{lo:.2f}-{hi:.2f}":>16s} {np.ptp(bbo[w]):12.4e} {bbo[w].mean():13.8f}')

print()
print('=' * 96)
print('4. GUI-DECLARED vs ENGINE STEP CONTROL, THE DECISIVE DIFFERENCE')
print('=' * 96)


def gui_traces(path):
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


g = gui_traces(E / 'S03_GUI_COLD_20us_gra.xml')
gt = g['V(v1)'][0]
gdt = np.diff(gt)
m = t <= gt[-1]
edt = np.diff(t[m])
print(f'  {"":34s} {"GUI":>14s} {"ENGINE":>14s}')
for nm, fn in [('median step (ps)', lambda d: np.median(d) * 1e12),
               ('mean step (ps)', lambda d: d.mean() * 1e12),
               ('% of steps at the ceiling', lambda d: 100 * (d > 0.999 * min(1e-9, CAP)).mean()),
               ('accepted points over 225 ns', lambda d: len(d)),
               ('deepest step at the event (ps)', lambda d: d.min() * 1e12)]:
    print(f'  {nm:34s} {fn(gdt):14.3f} {fn(edt):14.3f}')

# ------------------------------------------------------------------ plot
fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=False)

ge = gt <= 260e-9
m = t <= 260e-9
ax = axes[0]
ax.plot(t[m] * 1e9, v[m, 1], lw=1.0, label='ENGINE V(bb_in)')
ax.plot(gt[ge] * 1e9, g['V(bb_in)'][1][ge], lw=1.0, ls='--',
        label='GUI V(bb_in) (dies)')
ax.axvline(EVENT * 1e9, color='crimson', lw=1.2, ls=':',
           label=f'7 carrier periods = {EVENT*1e9:.3f} ns')
ax.set_ylabel('V(bb_in)  [V]')
ax.set_title('Cold start: identical netlist, two solver entry points')
ax.legend(fontsize=8, loc='best')
ax.grid(alpha=.3)

ax = axes[1]
ax.semilogy(t[m][1:] * 1e9, np.diff(t[m]) * 1e12, lw=1.0, label='ENGINE step')
ax.semilogy(gt[ge][1:] * 1e9, np.diff(gt[ge]) * 1e12, lw=1.0, ls='--',
            label='GUI step')
ax.axvline(EVENT * 1e9, color='crimson', lw=1.2, ls=':')
ax.axhline(CAP * 1e12, color='gray', lw=.9, ls='-.',
           label=f'ceiling = period/32 = {CAP*1e12:.1f} ps')
ax.set_ylabel('accepted time step  [ps]')
ax.set_title('The GUI takes ~3x smaller steps, then collapses at the event')
ax.legend(fontsize=8, loc='lower left')
ax.grid(alpha=.3, which='both')

ax = axes[2]
ax.plot(gt[ge][1:] * 1e9, np.diff(gt[ge]) * 1e12, lw=1.1, color='darkorange')
ax.axvline(EVENT * 1e9, color='crimson', lw=1.2, ls=':')
ax.set_yscale('log')
ax.set_xlim(224.5, 226.0)
ax.set_xlabel('time  [ns]')
ax.set_ylabel('GUI time step  [ps]')
ax.set_title('GUI end-game: step halved toward zero at the event -> ABORT')
ax.grid(alpha=.3, which='both')

fig.tight_layout()
fig.savefig(OUT / 'gui_failure_diagnosis.png', dpi=140)
print()
print(f'  plot written: {OUT / "gui_failure_diagnosis.png"}')

(OUT / 'event_characterisation.json').write_text(json.dumps({
    'event_s': EVENT, 'period_s': PERIOD, 'ceiling_s': CAP,
    'gui_median_step_s': float(np.median(gdt)),
    'engine_median_step_s': float(np.median(edt)),
    'gui_deepest_step_s': float(gdt.min()),
    'engine_deepest_step_s': float(edt.min()),
}, ensure_ascii=False, indent=2), encoding='utf-8')
