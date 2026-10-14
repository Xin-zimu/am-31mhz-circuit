import sys, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
ENG = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
order = ['T1_base','T2_opt_loose','T3_opt_tight','T4_set_loose','T5_set_rshunt1','T6_opt_rshunt1']
data = {}
for n in order:
    p = ENG / f'{n}.raw'
    if not p.exists(): print(n,'MISSING'); continue
    vn, v = read_raw(p); data[n] = v
    print('%-16s pts=%-6d end=%.6e  v1[-1]=%10.6f bbo[-1]=%10.6f v2[-1]=%10.6f' % (
        n, v.shape[0], v[-1,0], v[-1,3], v[-1,2], v[-1,4]))
print()
base = data['T1_base']
for n in order[1:]:
    v = data[n]
    if v.shape != base.shape:
        print('%-16s different shape %s vs %s' % (n, v.shape, base.shape)); continue
    d = np.abs(v - base)
    print('%-16s vs T1_base: identical=%s  maxdiff=%.4e' % (n, np.array_equal(v, base), d.max()))
