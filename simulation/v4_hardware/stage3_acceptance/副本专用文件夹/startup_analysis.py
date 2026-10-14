"""S03-04 startup characterisation: genuine zero-IC cold start, engine-validated.

Compares the cold start (Z_2ms_1ns / Z_2ms_2ns, all element ICs = 0) against the
accepted nominal precharged baseline, and reports when the output settles.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw

P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def load(n):
    vn, v = read_raw(P/(n+'.raw'))
    return vn, v

vn, cold = load('Z_2ms_1ns')
_, cold2 = load('Z_2ms_2ns')
t = cold[:,0]; v1 = cold[:,3]; bb = cold[:,1]; bbo = cold[:,2]; v2 = cold[:,4]

report = {'case': 'genuine zero IC cold start', 'points': int(cold.shape[0]), 'end_s': float(t[-1]),
          'tmax_effective_ns': float(np.diff(t).max()*1e9)}

# first samples
report['first_samples'] = [
    {'t_s': float(t[i]), 'V(bb_in)': float(bb[i]), 'V(bbo)': float(bbo[i]),
     'V(v1)': float(v1[i]), 'V(v2)': float(v2[i])} for i in range(4)]

# did it start from zero?
report['cold_zero_confirmed_mV'] = {
    'V(bb_in)': float(bb[1]*1e3), 'V(bbo)': float(bbo[1]*1e3),
    'V(v1)': float(v1[1]*1e3), 'V(v2)': float(v2[1]*1e3)}

# envelope over time using 20 us windows on V(v2) and V(v1)
def envelope(tt, yy, win=2e-5):
    out = []
    edges = np.arange(0, tt[-1]+win, win)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (tt >= a) & (tt < b)
        if m.sum() < 20: continue
        out.append({'t0_s': float(a), 't1_s': float(b),
                    'min': float(yy[m].min()), 'max': float(yy[m].max()),
                    'mean': float(yy[m].mean())})
    return out

report['v2_envelope_first_10'] = envelope(t, v2)[:10]
report['v1_envelope_first_10'] = envelope(t, v1)[:10]

# settle: last 5 complete input periods vs earlier windows
period = 1/20000
tail = t > t[-1] - 5*period
report['tail_last5_periods'] = {
    'V(v2)_mean': float(v2[tail].mean()), 'V(v2)_min': float(v2[tail].min()), 'V(v2)_max': float(v2[tail].max()),
    'V(v1)_mean': float(v1[tail].mean()), 'V(v1)_min': float(v1[tail].min()), 'V(v1)_max': float(v1[tail].max())}

# when does V(v2) envelope first come within 1% of the tail mean?
tailmean = float(v2[tail].mean())
env = envelope(t, v2, 2e-5)
settle = None
for e in env:
    if abs(e['mean'] - tailmean) < 0.01*abs(tailmean):
        # require the next 10 windows to also qualify
        i = env.index(e)
        if all(abs(x['mean'] - tailmean) < 0.01*abs(tailmean) for x in env[i:i+10]):
            settle = e['t0_s']; break
report['v2_settle_within_1pct_s'] = settle

# cold vs precharged (engine nominal) at the same times late in the run
nom = KEEP.parent/'engine_reference_2ms.npz'
z = np.load(nom, allow_pickle=True); nd = z['data']
nt = nd[:,0]
m = (t >= nt[0]) & (t <= nt[-1])
interp = {k: np.interp(t[m], nt, nd[:,i]) for k, i in [('bb_in',1),('bbo',2),('v1',3),('v2',4)]}
report['cold_vs_precharged_2ms'] = {
    k: {'max_abs_diff_V': float(np.abs(cold[m, i] - interp[k]).max()),
        'rms_diff_V': float(np.sqrt(np.mean((cold[m, i] - interp[k])**2)))}
    for k, i in [('bb_in',1),('bbo',2),('v1',3),('v2',4)]}

(KEEP/'startup_characterisation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=1)[:3000])
