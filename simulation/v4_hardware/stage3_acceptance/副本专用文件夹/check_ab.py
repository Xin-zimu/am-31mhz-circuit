import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
SCRATCH = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
a = (SCRATCH/'A_ref.raw').read_bytes(); b = (SCRATCH/'B_xspice_default.raw').read_bytes()
print('byte identical:', a == b, len(a), len(b))
na, va = read_raw(SCRATCH/'A_ref.raw'); nb, vb = read_raw(SCRATCH/'B_xspice_default.raw')
print('names:', na)
print('array identical:', np.array_equal(va, vb), va.shape, vb.shape)
if not np.array_equal(va, vb):
    d = np.abs(va-vb)
    print('max abs diff:', d.max(), 'at', np.unravel_index(np.argmax(d), d.shape))
    print('rows differing:', int(np.sum(np.any(d>0, axis=1))))
# compare with the documented engine run
nc, vc = read_raw(Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw'))
print('vs documented cold_engine_gui_net identical:', np.array_equal(va, vc), va.shape, vc.shape)
