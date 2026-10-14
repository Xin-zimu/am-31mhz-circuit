"""Step 1b: step-size and trajectory detail in the 150-300 ns window."""
import sys, json
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
SCRATCH = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = SRC / '副本专用文件夹'

def dec(name):
    out = {}
    for tr in ET.parse(SRC / name).iter('CTrace'):
        d = tr.find('Data')
        if d is None: continue
        lab = tr.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8')
        out[lab] = (x, y)
    return out

g = dec('S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml')
names, v = read_raw(SCRATCH / 'cold_engine_gui_net.raw')
et, eb, ebb, ev1, ev2 = v[:,0], v[:,1], v[:,2], v[:,3], v[:,4]

print('=== GUI last 15 accepted steps (V(v1) trace time axis) ===')
gx = g['V(v1)'][0]
for i in range(len(gx)-15, len(gx)):
    print('  i=%4d t=%.9e dt=%.4e  v1=%.6f  bb_in=%.6f  bbo=%.6f  v2=%.6f' % (
        i, gx[i], gx[i]-gx[i-1], g['V(v1)'][1][i], g['V(bb_in)'][1][i], g['V(bbo)'][1][i], g['V(v2)'][1][i]))

print()
print('=== engine accepted steps in 200-260 ns ===')
m = (et >= 2.00e-7) & (et <= 2.60e-7)
idx = np.flatnonzero(m)
print('count in window:', len(idx))
for i in idx:
    print('  i=%5d t=%.9e dt=%.4e  v1=%.6f  bb_in=%.8f  bbo=%.8f  v2=%.8f' % (
        i, et[i], et[i]-et[i-1], ev1[i], ebb[i], eb[i], ev2[i]))

print()
print('=== engine step count and dt distribution, first 300 ns ===')
mm = et <= 3.0e-7
d = np.diff(et[mm])
print('points <=300ns:', int(mm.sum()), ' dt min=%.4e max=%.4e mean=%.4e' % (d.min(), d.max(), d.mean()))
print('n dt at tmax(1.008ns):', int(np.sum(np.isclose(d, 1.008064516129043e-09))))
print()
print('=== GUI step count and dt distribution, whole captured range ===')
gd = np.diff(gx)
print('points:', len(gx), ' dt min=%.4e max=%.4e' % (gd.min(), gd.max()))
print('n dt == 1.008ns:', int(np.sum(np.isclose(gd, 1.008064516129043e-09))), ' n dt == 2ns:', int(np.sum(np.isclose(gd, 2e-9))))
