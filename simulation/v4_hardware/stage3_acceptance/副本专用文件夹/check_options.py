import sys, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
ENG = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
names = ['O0_none','O1_gui_all','O5_gear','O6_xspice_def']
ref = None
for n in names:
    p = ENG / f'{n}.raw'
    if not p.exists():
        print(n, 'MISSING'); continue
    b = p.read_bytes()
    vn, v = read_raw(p)
    print('%-16s bytes=%-8d pts=%-6d end=%.6e  sha=%s' % (n, len(b), v.shape[0], v[-1,0], hashlib.sha256(b).hexdigest()[:16]))
    if ref is None:
        ref = (n, v)
    else:
        same = np.array_equal(v, ref[1])
        d = np.abs(v - ref[1]).max() if v.shape == ref[1].shape else float('nan')
        print('%-16s identical to %s: %s  maxdiff=%.3e' % ('', ref[0], same, d))

# Compare with the documented failing GUI run window (226 ns) and engine 20us run
doc = read_raw(Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw'))
print()
print('documented engine 20us run: pts=%d end=%.6e' % (doc[1].shape[0], doc[1][-1,0]))
# where do these 2us runs sit at 2.26e-7?
for n in names:
    p = ENG / f'{n}.raw'
    if not p.exists(): continue
    vn, v = read_raw(p)
    t = v[:,0]
    i = int(np.searchsorted(t, 2.25984e-7))
    print('%-16s at t~226ns: i=%d t=%.9e v1=%.6f bb_in=%.6f bbo=%.6f v2=%.6f' % (n, i, t[i], v[i,3], v[i,1], v[i,2], v[i,4]))
