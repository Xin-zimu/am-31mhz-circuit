"""Compare the GUI 2 ms nominal step profile with the engine 2 ms reference."""
import sys
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))

WS = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS / '副本专用文件夹'

def dec(name, label='V(v1)'):
    for tr in ET.parse(WS/name).iter('CTrace'):
        d = tr.find('Data')
        if d is None: continue
        if tr.get('Name').removeprefix('&ASC') == label:
            return (np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8'),
                    np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8'))
    raise KeyError((name, label))

z = np.load(WS/'engine_reference_2ms.npz', allow_pickle=True)
data, names = z['data'], list(z['names'])
print('engine names:', names, 'shape:', data.shape)
et = data[:,0]
gx, gv = dec('S03_GUI_2ms_V4_3.decoded.xml')
print('GUI 2ms points=%d end=%.9e' % (len(gx), gx[-1]))
print('engine 2ms points=%d end=%.9e' % (len(et), et[-1]))

def stats(t, tag):
    d = np.diff(t)
    print('%s dt: min=%.4e max=%.4e median=%.4e' % (tag, d.min(), d.max(), np.median(d)))
    for frac in [0.01, 0.05, 0.25, 0.5, 0.9, 1.0]:
        tt = t[t <= t[-1]*frac]
        if len(tt) < 2: continue
        print('   by t<=%5.0f%% of end: npts=%-8d dt_max=%.4e' % (frac*100, len(tt), np.diff(tt).max()))
stats(gx, 'GUI   ')
stats(et, 'ENGINE')

print()
print('first 14 steps:')
for k in range(14):
    print('  k=%2d GUI t=%.9e dt=%.3e | ENGINE t=%.9e dt=%.3e' % (
        k, gx[k], (gx[k]-gx[k-1]) if k else 0, et[k], (et[k]-et[k-1]) if k else 0))
