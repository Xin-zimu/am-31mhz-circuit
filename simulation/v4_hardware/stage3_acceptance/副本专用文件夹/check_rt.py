import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
for n in ['RT_ideal','RT_1ns','RT_10ns','RT_100ns']:
    p = P/(n+'.raw')
    if not p.exists(): print('%-10s MISSING'%n); continue
    vn, v = read_raw(p)
    print('%-10s pts=%-7d end=%.4e bb_in[0..3]=%s' % (n, v.shape[0], v[-1,0], np.round(v[1:4,1],6)))
