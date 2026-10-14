"""Cold start vs the accepted 5 ms precharged nominal, same window."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
WS = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS/'副本专用文件夹'

vn, c = read_raw(P/'L_5ms_1ns.raw')
z = np.load(WS/'nominal_5ms.npz', allow_pickle=True)
nd = z['data']; names = list(z['names'])
print('nominal_5ms names:', names, 'shape:', nd.shape)

ct, cbb, cbbo, cv1, cv2 = c[:,0], c[:,1], c[:,2], c[:,3], c[:,4]
nt = nd[:,0]

def win(y, a, b):
    m = (ct>=a)&(ct<b); return (float(y[m].min()), float(y[m].max()), float(y[m].mean()))
def nwin(y, a, b):
    m = (nt>=a)&(nt<b); return (float(y[m].min()), float(y[m].max()), float(y[m].mean()))

print()
print('window       COLD V(v2) min/max/mean        PRECHARGED V(v2) min/max/mean')
for a,b in [(2e-3,3e-3),(3e-3,4e-3),(4e-3,5e-3)]:
    x = win(cv2,a,b); y = nwin(nd[:,4],a,b)
    print('  %.0f-%.0f ms   %.4f %.4f %.4f            %.4f %.4f %.4f' % (a*1e3,b*1e3,x[0],x[1],x[2],y[0],y[1],y[2]))

print()
print('window       COLD V(bb_in) min/max/mean       PRECHARGED V(bb_in)')
for a,b in [(2e-3,3e-3),(3e-3,4e-3),(4e-3,5e-3)]:
    x = win(cbb,a,b); y = nwin(nd[:,1],a,b)
    print('  %.0f-%.0f ms   %.4f %.4f %.4f            %.4f %.4f %.4f' % (a*1e3,b*1e3,x[0],x[1],x[2],y[0],y[1],y[2]))

# last complete input cycle comparison: freq and duty via crossings
def cycles(t, y, thresh):
    s = y > thresh
    idx = np.flatnonzero(np.diff(s.astype(int)) == 1)
    return t[idx]

# measure V(v2) crossings above 2 V in last 0.2 ms
m = ct > 4.8e-3; mn = nt > 4.8e-3
cc = cycles(ct[m], cv2[m], 2.0)
nn = cycles(nt[mn], nd[mn,4], 2.0)
print()
if len(cc) > 2 and len(nn) > 2:
    per_c = np.mean(np.diff(cc)); per_n = np.mean(np.diff(nn))
    print('V(v2) rising crossings in last 0.2 ms: cold n=%d period=%.6e s (%.3f Hz)' % (len(cc), per_c, 1/per_c))
    print('                                       nominal n=%d period=%.6e s (%.3f Hz)' % (len(nn), per_n, 1/per_n))
else:
    print('crossings cold=%d nominal=%d' % (len(cc), len(nn)))
