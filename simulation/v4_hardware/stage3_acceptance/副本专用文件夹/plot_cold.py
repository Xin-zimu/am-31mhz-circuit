"""Figure: cold start (zero IC) vs accepted precharged nominal baseline."""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

vn, c = read_raw(P/'Z_2ms_1ns.raw')
z = np.load(KEEP.parent/'engine_reference_2ms.npz', allow_pickle=True); nd = z['data']

fig, axes = plt.subplots(3, 2, figsize=(15, 11))
labels = [('V(bb_in)', 1), ('V(bbo)', 2), ('V(v2)', 4)]

# left column: full 2 ms
for ax, (lbl, i) in zip(axes[:, 0], labels):
    ax.plot(nd[:, 0]*1e3, nd[:, i], lw=0.6, color='tab:blue', label='precharged (accepted)')
    ax.plot(c[:, 0]*1e3, c[:, i], lw=0.6, color='tab:red', label='zero IC cold start')
    ax.set_title('%s  full 2 ms' % lbl); ax.set_xlabel('ms'); ax.set_ylabel('V'); ax.grid(alpha=.3)
    ax.legend(fontsize=8)

# right column: first 200 us
for ax, (lbl, i) in zip(axes[:, 1], labels):
    m = c[:, 0] <= 2e-4
    mn = nd[:, 0] <= 2e-4
    ax.plot(nd[mn, 0]*1e6, nd[mn, i], lw=0.8, color='tab:blue', label='precharged')
    ax.plot(c[m, 0]*1e6, c[m, i], lw=0.8, color='tab:red', label='cold start')
    ax.set_title('%s  first 200 us' % lbl); ax.set_xlabel('us'); ax.set_ylabel('V'); ax.grid(alpha=.3)
    ax.legend(fontsize=8)

fig.suptitle('S03-04  cold start (all element IC = 0) vs accepted precharged 2 ms baseline\n'
             'same circuit, same options, engine TMAX = 1 ns', fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
out = KEEP/'S03_04_cold_vs_nominal.png'
fig.savefig(out, dpi=110)
print('saved', out, out.stat().st_size, 'bytes')
