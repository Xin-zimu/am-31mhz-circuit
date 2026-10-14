"""Step 1b: timestep profile. Why does the GUI's step collapse while the engine's does not?"""
import sys, json
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
SCRATCH = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = SRC / '副本专用文件夹'
TMAX = 1.0080645161290323e-09

def dec(name):
    for tr in ET.parse(SRC / name).iter('CTrace'):
        d = tr.find('Data')
        if d is None: continue
        if tr.get('Name').removeprefix('&ASC') == 'V(v1)':
            x = np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8')
            y = np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8')
            return x, y
    raise KeyError(name)

gx, gv1 = dec('S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml')
gd = np.diff(gx)
print('GUI: points=%d  end=%.6e' % (len(gx), gx[-1]))
print('GUI dt: min=%.4e max=%.4e' % (gd.min(), gd.max()))
print('GUI dt == TMAX(1.008ns) exactly :', int(np.sum(gd == TMAX)))
print('GUI dt == TMAX/2               :', int(np.sum(gd == TMAX/2)))
print('GUI dt <  TMAX                 :', int(np.sum(gd < TMAX)))
first_lt = int(np.flatnonzero(gd < TMAX)[0])
print('first dt<TMAX at index %d, t=%.9e, dt=%.4e' % (first_lt, gx[first_lt], gd[first_lt]))
print()
print('GUI step history: every index where dt changes regime (first 40 deviations)')
dev = np.flatnonzero(gd < TMAX)
prev = None
shown = 0
for k in dev:
    d = gd[k]
    if prev is None or not np.isclose(d, prev, rtol=1e-6):
        print('   i=%4d t=%.9e dt=%.4e  dt/TMAX=%.4f' % (k, gx[k], d, d/TMAX))
        prev = d
        shown += 1
        if shown >= 40: 
            print('   ...')
            break
print()
print('GUI dt histogram (decades relative to TMAX):')
r = gd / TMAX
for lo in [1.0, 0.5, 0.25, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6, 1e-9]:
    print('   dt/TMAX < %g : %d' % (lo, int(np.sum(r < lo))))

names, v = read_raw(SCRATCH / 'cold_engine_gui_net.raw')
et = v[:,0]
ed = np.diff(et)
print()
print('ENGINE: points=%d end=%.6e' % (len(et), et[-1]))
print('ENGINE dt: min=%.4e max=%.4e   dt==TMAX: %d / %d' % (ed.min(), ed.max(), int(np.sum(ed == TMAX)), len(ed)))
first_e = int(np.flatnonzero(ed < TMAX)[0])
print('first dt<TMAX at index %d t=%.9e dt=%.4e' % (first_e, et[first_e], ed[first_e]))

# byte-compare the two engine trials
a = (SCRATCH/'A_ref.raw').read_bytes()
b = (SCRATCH/'B_xspice_default.raw').read_bytes()
print()
print('A_ref vs B_xspice_default raw identical bytes:', a == b, len(a), len(b))
na, va = read_raw(SCRATCH/'A_ref.raw'); nb, vb = read_raw(SCRATCH/'B_xspice_default.raw')
print('A_ref vs B identical arrays:', np.array_equal(va, vb))
