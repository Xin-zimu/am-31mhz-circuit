import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
import time
for _ in range(40):
    if (P/'R6_opt_method.raw').exists(): break
    time.sleep(5)
ref=None
for n in ['R0_plain','R1_opt_loose','R2_opt_tight','R3_set_loose','R4_set_tight','R5_set_tmax','R6_opt_method']:
    p=P/f'{n}.raw'
    if not p.exists(): print('%-15s MISSING'%n); continue
    vn,v=read_raw(p)
    if ref is None:
        ref=v; print('%-15s pts=%-6d end=%.4e  (REFERENCE)'%(n,v.shape[0],v[-1,0]))
    else:
        same = v.shape==ref.shape and np.array_equal(v,ref)
        d = np.abs(v[:min(len(v),len(ref))]-ref[:min(len(v),len(ref))]).max() if v.shape[1]==ref.shape[1] else float('nan')
        print('%-15s pts=%-6d end=%.4e  identical=%s maxdiff=%.3e'%(n,v.shape[0],v[-1,0],same,d))
