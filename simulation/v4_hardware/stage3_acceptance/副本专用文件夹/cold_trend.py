"""Is the cold start converging, just slowly? Fit the bias build-up trend."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')

vn, c = read_raw(P/'Z_2ms_1ns.raw')
t, bb, bbo, v1, v2 = c[:,0], c[:,1], c[:,2], c[:,3], c[:,4]

# window means for V(bb_in) and V(v2)
edges = [0,2e-5,1e-4,2e-4,4e-4,6e-4,8e-4,1e-3,1.2e-3,1.4e-3,1.6e-3,1.8e-3,2e-3]
rows = []
for a,b in zip(edges[:-1], edges[1:]):
    m=(t>=a)&(t<b)
    rows.append((a,b,float(bb[m].mean()),float(v2[m].mean()),float(bbo[m].mean())))

print('window(ms)      V(bb_in)   V(v2)     V(bbo)')
for a,b,x,y,z in rows:
    print('  %6.3f-%6.3f  %9.5f %9.5f %9.5f' % (a*1e3,b*1e3,x,y,z))

# exponential fit for bb_in toward 4.5 V: ln(4.5-bb) linear in t?
tm = np.array([(a+b)/2 for a,b,_,_,_ in rows])
bbm = np.array([x for _,_,x,_,_ in rows])
for A in [4.5, 4.6, 4.7]:
    rem = A - bbm
    ok = rem > 0
    if ok.sum() > 4:
        p = np.polyfit(tm[ok], np.log(rem[ok]), 1)
        tau = -1/p[0]
        print('assume asymptote %.2f V -> tau = %.4f ms ; predicted V(bb_in) at 5 ms = %.4f V' % (A, tau*1e3, A-(A-bbm[ok][-1])*np.exp(-(5e-3-tm[ok][-1])/tau)))
print()
print('V(bb_in) last value: %.6f ; V(v2) last: %.6f' % (bb[-1], v2[-1]))
