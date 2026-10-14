"""State the engine/GUI asymmetry precisely."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
_, v = read_raw(P/'M_2n_2n.raw')
print('ENGINE with TSTEP=TMAX=2ns (the GUI failing setting):')
print('  points=%d end=%.6e  -> reached the full 2 us window' % (v.shape[0], v[-1,0]))
print('  dtmax=%.6e (the same 1.008065 ns cap the GUI had)' % np.diff(v[:,0]).max())
print()
print('GUI with TSTEP=TMAX=2ns: stopped at 2.25e-07 s (measured, reproducible)')
print('=> the cap value alone does NOT explain the GUI failure; the GUI solver')
print('   behaves differently from the command-interface engine at ~225 ns.')
