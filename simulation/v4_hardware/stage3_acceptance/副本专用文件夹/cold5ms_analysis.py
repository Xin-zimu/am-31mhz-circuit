"""When does the cold start reach the nominal operating point? 5 ms evidence."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

vn, c = read_raw(P/'L_5ms_1ns.raw')
t, bb, bbo, v1, v2 = c[:,0], c[:,1], c[:,2], c[:,3], c[:,4]

# nominal tail values (from the accepted precharged 2 ms baseline, last window)
z = np.load(KEEP.parent/'engine_reference_2ms.npz', allow_pickle=True); nd = z['data']
nt = nd[:,0]
nom = {}
for lbl, i in [('bb_in',1),('bbo',2),('v1',3),('v2',4)]:
    m = nt > 1.5e-3
    nom[lbl] = float(nd[m, i].mean())
print('nominal last-0.5ms means:', {k: round(v, 4) for k, v in nom.items()})

# instantaneous V(v2) envelope in 50 us windows; report when it first stays >= 2 V
env = []
edges = np.arange(0, t[-1] + 5e-5, 5e-5)
for a, b in zip(edges[:-1], edges[1:]):
    m = (t >= a) & (t < b)
    if m.sum() < 50: continue
    env.append((a, float(v2[m].min()), float(v2[m].max()), float(v2[m].mean())))

first_hi = None
for i, (a, mn, mx, me) in enumerate(env):
    if mn >= 1.0 and all(e[1] >= 1.0 for e in env[i:i+20]):
        first_hi = a; break

# first window whose mean is within 1% of the nominal window mean
first_near = None
for a, mn, mx, me in env:
    if a > 1e-3 and abs(me - nom['v2']) < 0.05*abs(nom['v2']):
        first_near = a; break

# settling proxy: last time V(v2) instantaneous is below 1 V
below = np.flatnonzero(v2 < 1.0)
last_below = float(t[below[-1]]) if len(below) else None

rep = {'points': int(c.shape[0]), 'end_s': float(t[-1]),
       'first_time_v2_stays_above_1V_s': first_hi,
       'first_time_v2_window_mean_within_5pct_nominal_s': first_near,
       'last_time_v2_below_1V_s': last_below,
       'nominal_last_0p5ms_means': nom,
       'v2_last_100us': {'min': float(v2[t>4.9e-3].min()), 'max': float(v2[t>4.9e-3].max()),
                          'mean': float(v2[t>4.9e-3].mean())},
       'bb_in_last': float(bb[-1])}
(KEEP/'cold_start_5ms_analysis.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(rep, ensure_ascii=False, indent=1))
