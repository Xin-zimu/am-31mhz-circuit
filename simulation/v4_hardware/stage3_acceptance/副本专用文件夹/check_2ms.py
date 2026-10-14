import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
for n in ['Z_2ms_2ns','Z_2ms_1ns']:
    p = P/(n+'.raw')
    if not p.exists(): print(n,'MISSING'); continue
    vn, v = read_raw(p)
    d = np.diff(v[:,0])
    print('%-12s pts=%-9d end=%.9e dt_min=%.3e dt_max=%.3e v1[-1]=%.6f' % (n, v.shape[0], v[-1,0], d.min(), d.max(), v[-1,3]))
