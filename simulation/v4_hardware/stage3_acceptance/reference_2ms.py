"""Measure the first 2 ms of the existing 5 ms engine record; not a new run."""
from pathlib import Path
import sys,json
import numpy as np
import measure_stage3 as established
HERE=Path(__file__).resolve().parent
z=np.load(HERE/'nominal_5ms.npz')
names=list(z['names']); full=z['data']
end=.002
a=full[full[:,0]<end]
last=np.array([end]+[np.interp(end,full[:,0],full[:,i]) for i in range(1,full.shape[1])])
a=np.vstack([a,last])
established.read_raw=lambda _: (names,a)
sys.argv=['measure_stage3.py',str(HERE/'engine_reference_2ms.raw')]
established.main()
p=HERE/'engine_reference_2ms_metrics.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['provenance']='First 2 ms extracted from existing nominal_5ms.npz; interpolated endpoint; not a new simulation'
p.write_text(json.dumps(d,indent=2),encoding='utf-8')
