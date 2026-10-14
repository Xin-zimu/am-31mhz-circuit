"""Figure: full 5 ms cold start vs accepted 5 ms precharged nominal."""
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

vn, c = read_raw(P/'L_5ms_1ns.raw')
z = np.load(WS/'nominal_5ms.npz', allow_pickle=True); nd = z['data']

fig, axes = plt.subplots(2, 2, figsize=(15, 9))
plots = [('V(bb_in)', 1), ('V(v2)', 4)]
for ax, (lbl, i) in zip(axes[:, 0], plots):
    ax.plot(nd[:, 0]*1e3, nd[:, i], lw=0.4, color='tab:blue', label='precharged (accepted)')
    ax.plot(c[:, 0]*1e3, c[:, i], lw=0.4, color='tab:red', label='zero IC cold start')
    ax.set_title('%s  full 5 ms' % lbl); ax.set_xlabel('ms'); ax.set_ylabel('V')
    ax.grid(alpha=.3); ax.legend(fontsize=8, markerscale=6)
for ax, (lbl, i) in zip(axes[:, 1], plots):
    a, b = 2e-3, 5e-3
    mc = (c[:,0] >= a) & (c[:,0] < b); mn = (nd[:,0] >= a) & (nd[:,0] < b)
    ax.plot(nd[mn, 0]*1e3, nd[mn, i], lw=0.5, color='tab:blue', label='precharged')
    ax.plot(c[mc, 0]*1e3, c[mc, i], lw=0.5, color='tab:red', label='cold start')
    ax.set_title('%s  2-5 ms (cold start coming up)' % lbl); ax.set_xlabel('ms'); ax.set_ylabel('V')
    ax.grid(alpha=.3); ax.legend(fontsize=8, markerscale=6)

fig.suptitle('S03-04  zero-IC cold start reaches the operating point only at ~4.2 ms\n'
             'same circuit, same options, engine TMAX = 1 ns', fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = KEEP/'S03_04_cold_5ms_vs_nominal.png'
fig.savefig(out, dpi=110)
print('saved', out.name, out.stat().st_size)
