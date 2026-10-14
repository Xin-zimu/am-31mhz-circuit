"""Does the cold start establish the nominal operating point? Full 2 ms view."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

vn, c = read_raw(P/'Z_2ms_1ns.raw')
t, bb, bbo, v1, v2 = c[:,0], c[:,1], c[:,2], c[:,3], c[:,4]

z = np.load(KEEP.parent/'engine_reference_2ms.npz', allow_pickle=True); nd = z['data']
nt = nd[:,0]

def win(y, a, b):
    m = (t>=a)&(t<b)
    return (float(y[m].min()), float(y[m].max()), float(y[m].mean())) if m.sum() else None

print('COLD (all element IC = 0), engine, TMAX=1ns')
print('  t range: %.3e .. %.3e  (%d pts)' % (t[0], t[-1], len(t)))
for lbl, y in [('V(bb_in)',bb), ('V(bbo)',bbo), ('V(v1)',v1), ('V(v2)',v2)]:
    print('  %-9s' % lbl, end='')
    for a,b in [(0,2e-5),(2e-5,1e-4),(1e-4,5e-4),(5e-4,1e-3),(1e-3,1.5e-3),(1.5e-3,2e-3)]:
        mn,mx,me = win(y,a,b)
        print(' [%.4f,%.4f]m=%.4f' % (mn,mx,me), end='')
    print()

print()
print('NOMINAL precharged baseline (engine 2ms), same windows')
for lbl, i in [('V(bb_in)',1),('V(bbo)',2),('V(v1)',3),('V(v2)',4)]:
    y = nd[:,i]
    print('  %-9s' % lbl, end='')
    for a,b in [(0,2e-5),(2e-5,1e-4),(1e-4,5e-4),(5e-4,1e-3),(1e-3,1.5e-3),(1.5e-3,2e-3)]:
        m=(nt>=a)&(nt<b)
        print(' [%.4f,%.4f]m=%.4f' % (y[m].min(),y[m].max(),y[m].mean()), end='')
    print()

# last 100 us
print()
print('tail 1.9-2.0 ms:')
m = t>1.9e-3
for lbl,y in [('V(bb_in)',bb),('V(bbo)',bbo),('V(v1)',v1),('V(v2)',v2)]:
    print('  %-9s min=%.6f max=%.6f mean=%.6f' % (lbl, y[m].min(), y[m].max(), y[m].mean()))
