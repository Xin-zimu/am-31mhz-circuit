"""Confirm the mixed-variant result: engine free-run with different TSTEP/TMAX caps."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')

def tailcheck(n):
    vn, v = read_raw(P/(n+'.raw'))
    t = v[:,0]
    # the run only reaches the failure point if the trace stops short of 2us
    dt = np.diff(t)
    return dict(name=n, points=int(v.shape[0]), end_s=float(t[-1]), dtmax=float(dt.max()), dtmin=float(dt.min()),
                reached_2us=bool(abs(t[-1]-2e-6) < 1e-15))

for n in ['M_2n_2n','M_1n_1n','M_2n_1n','M_1n_2n','M_05n_2n','M_1n_10n','M_1n_1008p','M_2n_1008p']:
    p = P/(n+'.raw')
    if not p.exists(): print(n, 'MISSING'); continue
    c = tailcheck(n)
    print('%-12s pts=%-7d end=%.4e dtmax=%.6e reached2us=%s' % (c['name'], c['points'], c['end_s'], c['dtmax'], c['reached_2us']))

# The decisive engine free-run: which caps avoid failure?
print()
print('Engine free-run verdict (did it reach 2 us?):')
for n in ['M_2n_2n','M_1n_1n','M_2n_1n','M_1n_2n']:
    p = P/(n+'.raw')
    if not p.exists(): continue
    _, v = read_raw(p)
    print('  %-10s %s' % (n, 'REACHED 2us' if abs(v[-1,0]-2e-6)<1e-15 else 'STOPPED at %.4e' % v[-1,0]))
