import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
# Investigate the divergence mechanism: is the GUI applying a smaller first step?
_, u0 = read_raw(P/'U00_none.raw') if (P/'U00_none.raw').exists() else (None,None)
# Re-derive from the existing 2us O0 run vs the 20us documented run (same settings)
_, a = read_raw(P/'O0_none.raw')          # 2n 2u 0 2n
_, b = read_raw(Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw'))   # 2n 20u 0 2n
n = min(len(a), len(b))
print('O0_none(2us) vs cold_engine_gui_net(20us), first', n, 'points')
print('time axes identical for first %d: %s' % (n, np.allclose(a[:n,0], b[:n,0], rtol=0, atol=0)))
for k in range(n):
    if a[k,0] != b[k,0]:
        print('first time-axis divergence at k=%d: %.6e vs %.6e' % (k, a[k,0], b[k,0])); break
print('max value diff over common prefix: %.3e' % np.abs(a[:n,1:]-b[:n,1:]).max())

# Compare O0 (2us) end behaviour
print()
print('O0_none last 5:')
for k in range(len(a)-5, len(a)):
    print('  t=%.9e v1=%.6f' % (a[k,0], a[k,3]))
