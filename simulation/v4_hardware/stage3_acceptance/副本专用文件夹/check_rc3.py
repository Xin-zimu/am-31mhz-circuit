import sys, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
names = ['S0_plain','S1_opt_loose','S2_opt_tight','S3_set_loose','S4_set_tight','S5_opt_gear','S6_set_gear']
ref = None
data = {}
for n in names:
    p = P/f'{n}.raw'
    vn, v = read_raw(p); data[n] = v
    if ref is None:
        ref = v; print('%-14s pts=%-6d  (REFERENCE) %s' % (n, v.shape[0], vn))
    else:
        same = v.shape == ref.shape and np.array_equal(v, ref)
        d = np.abs(v-ref).max() if v.shape == ref.shape else float('nan')
        print('%-14s pts=%-6d  identical_to_ref=%-5s maxdiff=%.3e' % (n, v.shape[0], same, d))
print()
print('time axis first 12 steps for S0 vs S1 vs S2:')
for k in range(12):
    print('  k=%2d  %-14.8e %-14.8e %-14.8e' % (k, data['S0_plain'][k,0], data['S1_opt_loose'][k,0], data['S2_opt_tight'][k,0]))
