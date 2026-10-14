"""Step 1b: compare GUI decoded traces against engine raw traces at common times."""
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

names, vals = read_raw(SCRATCH / 'cold_engine_gui_net.raw')
print('engine raw vars:', names, 'points:', vals.shape)

gui = dec('S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml')
et = vals[:, 0]
emap = {'V(bb_in)': 1, 'V(bbo)': 2, 'V(v1)': 3, 'V(v2)': 4}

report = {}
for lab, (gx, gy) in gui.items():
    ey = vals[:, emap[lab]]
    # engine interpolated at GUI sample times within engine range
    m = gx <= et[-1]
    interp = np.interp(gx[m], et, ey)
    diff = np.abs(interp - gy[m])
    firstbad = None
    idx = np.flatnonzero(diff > 1e-9)
    if len(idx):
        firstbad = {'index': int(idx[0]), 'time_s': float(gx[idx[0]]),
                    'gui_v': float(gy[idx[0]]), 'engine_v': float(interp[idx[0]]),
                    'abs_diff': float(diff[idx[0]])}
    report[lab] = {'compared_points': int(m.sum()),
                   'max_abs_diff_v': float(diff.max()),
                   'gui_end_s': float(gx[-1]),
                   'engine_at_gui_end_v': float(np.interp(gx[-1], et, ey)),
                   'gui_end_v': float(gy[-1]),
                   'first_abs_diff_gt_1nV': firstbad}

# engine stepping statistics
dt = np.diff(et)
print('\nengine min dt: %.4g s at t=%.6g' % (dt.min(), et[np.argmin(dt)]))
print('engine max dt: %.4g s at t=%.6g' % (dt.max(), et[np.argmax(dt)]))
sub = dt[et[:-1] < 2.26e-7]
print('engine dt over first 226 ns: min=%.4g max=%.4g npts=%d' % (sub.min(), sub.max(), len(sub) + 1))
gui_dt = np.diff(gui['V(v1)'][0])
print('GUI   dt over its range   : min=%.4g max=%.4g npts=%d' % (gui_dt.min(), gui_dt.max(), len(gui_dt) + 1))

print()
print(json.dumps(report, indent=1))
(OUT / 'step1b_trajectory_compare.json').write_text(json.dumps(
    {'engine': {'min_dt_s': float(dt.min()), 'max_dt_s': float(dt.max()),
                'points': int(len(et)), 'end_s': float(et[-1])},
     'per_trace': report}, indent=2), encoding='utf-8')
