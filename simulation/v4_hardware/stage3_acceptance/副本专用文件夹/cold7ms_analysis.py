"""7 ms cold start: does it converge to the precharged nominal operating point?"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
WS = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS/'副本专用文件夹'

vn, c = read_raw(P/'L_7ms_1ns.raw')
t, bb, bbo, v1, v2 = c[:,0], c[:,1], c[:,2], c[:,3], c[:,4]
z = np.load(WS/'nominal_5ms.npz', allow_pickle=True); nd = z['data']; nt = nd[:,0]

print('7 ms cold start: points=%d end=%.9e' % (c.shape[0], t[-1]))

# nominal tail means (last 0.5 ms of the accepted 5 ms run = 4.5-5.0 ms)
nom = {}
for lbl, i in [('bb_in',1),('bbo',2),('v2',4)]:
    m = nt > 4.5e-3
    nom[lbl] = float(nd[m,i].mean())
print('nominal 4.5-5.0 ms means:', {k: round(v,4) for k,v in nom.items()})

rep = {'points': int(c.shape[0]), 'end_s': float(t[-1]), 'nominal_tail_means': nom, 'windows': []}
edges = [0,1e-3,2e-3,3e-3,4e-3,4.5e-3,5e-3,5.5e-3,6e-3,6.5e-3,7e-3]
print()
print('window(ms)   V(bb_in)mean  V(v2)mean   V(v2)min  V(v2)max')
for a,b in zip(edges[:-1], edges[1:]):
    m=(t>=a)&(t<b)
    if m.sum()<50: continue
    row = {'t0':a,'t1':b,'bb_in_mean':float(bb[m].mean()),'v2_mean':float(v2[m].mean()),
           'v2_min':float(v2[m].min()),'v2_max':float(v2[m].max())}
    rep['windows'].append(row)
    print('  %4.1f-%4.1f   %9.4f   %9.4f  %8.4f %8.4f' % (a*1e3,b*1e3,row['bb_in_mean'],row['v2_mean'],row['v2_min'],row['v2_max']))

# last 0.5 ms vs nominal
m = t > t[-1]-0.5e-3
rep['cold_last_0p5ms'] = {'bb_in_mean': float(bb[m].mean()), 'v2_mean': float(v2[m].mean()),
                          'v2_min': float(v2[m].min()), 'v2_max': float(v2[m].max())}
print()
print('cold 6.5-7.0 ms:', {k: round(v,4) for k,v in rep['cold_last_0p5ms'].items()})
print('vs nominal 4.5-5.0 ms: bb_in %.4f  v2_mean %.4f' % (nom['bb_in'], nom['v2']))
rep['difference_vs_nominal'] = {
    'bb_in_mean_diff_V': rep['cold_last_0p5ms']['bb_in_mean'] - nom['bb_in'],
    'v2_mean_diff_V': rep['cold_last_0p5ms']['v2_mean'] - nom['v2']}
print('difference:', {k: round(v,4) for k,v in rep['difference_vs_nominal'].items()})

# when did v2 stabilise (window mean within 2% of nominal)?
for w in rep['windows']:
    if w['t1'] > 5e-3 and abs(w['v2_mean'] - nom['v2']) < 0.02*nom['v2']:
        rep['first_window_within_2pct_after_5ms'] = w['t0']; break

(KEEP/'cold_start_7ms_analysis.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(json.dumps({k:v for k,v in rep.items() if k!='windows'}, ensure_ascii=False, indent=1))
