"""Figure: 7 ms cold start converging onto the accepted precharged nominal."""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
WS = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS/'副本专用文件夹'

vn, c = read_raw(P/'L_7ms_1ns.raw')
z = np.load(WS/'nominal_5ms.npz', allow_pickle=True); nd = z['data']

t = c[:,0]; v2 = c[:,4]; bb = c[:,1]

# window means for a clean convergence view
edges = np.arange(0, 7.001e-3, 0.25e-3)
wm_t, wm_v2, wm_bb = [], [], []
nm_t, nm_v2, nm_bb = [], [], []
for a,b in zip(edges[:-1], edges[1:]):
    m=(t>=a)&(t<b); mn=(nd[:,0]>=a)&(nd[:,0]<b)
    if m.sum()>50: wm_t.append((a+b)/2*1e3); wm_v2.append(v2[m].mean()); wm_bb.append(bb[m].mean())
    if mn.sum()>50: nm_t.append((a+b)/2*1e3); nm_v2.append(nd[mn,4].mean()); nm_bb.append(nd[mn,1].mean())

nom_v2 = float(nd[nd[:,0]>4.5e-3,4].mean())
nom_bb = float(nd[nd[:,0]>4.5e-3,1].mean())

fig, axes = plt.subplots(2, 2, figsize=(15, 9))
ax = axes[0,0]
ax.plot(wm_t, wm_v2, 'o-', ms=3, color='tab:red', label='cold start V(v2) window mean')
ax.axhline(nom_v2, color='tab:blue', ls='--', lw=1.2, label='precharged nominal %.3f V' % nom_v2)
ax.axvline(4.218, color='gray', ls=':', lw=1, label='V(v2) last < 1 V (4.218 ms)')
ax.set_title('V(v2) window mean (0.25 ms windows)'); ax.set_xlabel('ms'); ax.set_ylabel('V')
ax.grid(alpha=.3); ax.legend(fontsize=8)

ax = axes[0,1]
ax.plot(wm_t, wm_bb, 'o-', ms=3, color='tab:red', label='cold start V(bb_in)')
ax.axhline(nom_bb, color='tab:blue', ls='--', lw=1.2, label='precharged nominal %.3f V' % nom_bb)
ax.set_title('V(bb_in) window mean'); ax.set_xlabel('ms'); ax.set_ylabel('V')
ax.grid(alpha=.3); ax.legend(fontsize=8)

ax = axes[1,0]
m = t>5e-3
ax.plot(t[m]*1e3, v2[m], lw=0.35, color='tab:red', label='cold start 5-7 ms')
mn = nd[:,0]>4e-3
ax.plot(nd[mn,0]*1e3, nd[mn,4], lw=0.35, color='tab:blue', label='precharged 4-5 ms')
ax.set_title('V(v2) waveform detail'); ax.set_xlabel('ms'); ax.set_ylabel('V')
ax.grid(alpha=.3); ax.legend(fontsize=8, markerscale=6)

ax = axes[1,1]
ax.plot(wm_t, [v - nom_v2 for v in wm_v2], 'o-', ms=3, color='tab:red')
ax.axhline(0, color='k', lw=0.8)
ax.set_title('V(v2) window mean minus nominal (%.3f V)' % nom_v2)
ax.set_xlabel('ms'); ax.set_ylabel('V'); ax.grid(alpha=.3)

fig.suptitle('S03-04  zero-IC cold start converges to the accepted operating point by ~6.5 ms\n'
             'same circuit, same options, engine TMAX = 1 ns', fontsize=12)
fig.tight_layout(rect=[0,0,1,0.93])
out = KEEP/'S03_04_cold_7ms_convergence.png'
fig.savefig(out, dpi=110)
print('saved', out.name, out.stat().st_size)
