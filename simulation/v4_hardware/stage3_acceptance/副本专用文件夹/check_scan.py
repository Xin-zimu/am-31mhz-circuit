import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmraw import read_raw
P = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
man = json.loads((P/'manifest_scan.json').read_text(encoding='utf-8'))
done = sorted(p.stem for p in P.glob('U*.raw'))
print('completed:', len(done), 'of', len(man['cases']))
ref = None
c=-0
rows=[]
for n in sorted(man['cases']):
    p = P/f'{n}.raw'
    if not p.exists(): continue
    try:
        _, v = read_raw(p)
    except Exception as e:
        rows.append((n,'READ-ERR',str(e)[:40])); continue
    if ref is None:
        ref=(n,v)
        rows.append((n,'REFERENCE', 'pts=%d end=%.3e' % (v.shape[0], v[-1,0])))
    else:
        same_shape = v.shape==ref[1].shape
        if same_shape:
            identical = np.array_equal(v,ref[1]); d=np.abs(v-ref[1]).max()
            rows.append((n,'SAME' if identical else 'DIFF', 'maxdiff=%.3e pts=%d' % (d, v.shape[0])))
        else:
            rows.append((n,'DIFF-LEN','pts=%d end=%.3e' % (v.shape[0], v[-1,0])))
for r in rows:
    print('%-20s %-10s %s' % r)
