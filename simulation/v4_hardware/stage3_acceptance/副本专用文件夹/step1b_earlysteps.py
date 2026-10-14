import sys
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
SCRATCH = Path(r'D:\ms_xsp\stage3_acceptance\s0304')

def dec(name):
    for tr in ET.parse(SRC/name).iter('CTrace'):
        d = tr.find('Data')
        if d is None: continue
        if tr.get('Name').removeprefix('&ASC')=='V(v1)':
            return (np.frombuffer(bytes.fromhex(d.get('XData')),dtype='<f8'),
                    np.frombuffer(bytes.fromhex(d.get('YData')),dtype='<f8'))
gx, gv = dec('S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml')
_, ev = read_raw(SCRATCH/'T1_base.raw')
et, ev1 = ev[:,0], ev[:,3]

# GUI 20us run vs engine 20us run at common times
_, ev20 = read_raw(Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw'))
e20t, e20v1 = ev20[:,0], ev20[:,3]

print('=== first 20 accepted steps: GUI vs engine ===')
print('  k |   GUI t        GUI dt      GUI v1   |  ENGINE t     ENGINE dt    ENGINE v1')
for k in range(0, 20):
    gdt = gx[k]-gx[k-1] if k>0 else 0.0
    edt = e20t[k]-e20t[k-1] if k>0 else 0.0
    print('%3d | %.6e %.3e %10.6f | %.6e %.3e %10.6f' % (k, gx[k], gdt, gv[k], e20t[k], edt, e20v1[k]))

print()
print('=== step magnitude growth: time at which each trace first exceeds X ns ===')
for X in [1e-12,1e-11,1e-10,1e-9,5e-9,1e-10*0+1e-9]:
    pass
for X in [1e-12,1e-11,1e-10,1e-9]:
    gi = np.flatnonzero(np.diff(gx) > X)
    ei = np.flatnonzero(np.diff(e20t) > X)
    print('  dt>%8.0e : GUI first at t=%-12.6e (k=%s) | ENGINE first at t=%-12.6e (k=%s)' % (
        X, gx[gi[0]+1] if len(gi) else float('nan'), gi[0] if len(gi) else '-',
        e20t[ei[0]+1] if len(ei) else float('nan'), ei[0] if len(ei) else '-'))
