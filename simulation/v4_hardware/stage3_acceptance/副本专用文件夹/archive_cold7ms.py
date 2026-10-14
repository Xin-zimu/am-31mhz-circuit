"""Archive the 7 ms cold-start arrays (settling evidence) to NPZ."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
vn, v = read_raw(P/'L_7ms_1ns.raw')
np.savez_compressed(KEEP/'cold_7ms_1ns.npz', data=v, names=np.array(vn, dtype=object))
out = KEEP/'cold_7ms_1ns.npz'
print('saved', out.name, out.stat().st_size, 'bytes', v.shape)
