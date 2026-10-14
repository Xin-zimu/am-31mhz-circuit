from pathlib import Path
import numpy as np,json
from design_stage1 import HERE,metrics
WORK=Path('D:/ms_xsp/v4_lm393')
def read_xsp(p):
    head,body=p.read_text().split('Values:',1)
    names=[l.split()[-1].lower() for l in head.split('\nVariables:',1)[1].splitlines() if l.strip()]
    a=np.array([float(l.split()[-1]) for l in body.splitlines() if l.strip()]).reshape(-1,len(names))
    return dict(zip(names,a.T))
if __name__=='__main__':
    rec=[]
    for p in WORK.glob('*.raw'):
        d=read_xsp(p)
        m={'name':p.stem,'points':len(d['time']),'end_s':d['time'][-1],'v1_min':d['v(v1)'].min(),'v1_max':d['v(v1)'].max()}
        if d['time'][-1]>.0014:m.update(metrics(d))
        print(m); rec.append(m)
    (HERE/'xspice_results.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
