"""Actual C4 + LM393 matrix. Max two independent simulator processes."""
import json,sys
from concurrent.futures import ThreadPoolExecutor
from alt2 import ROOT,run
from edges import assess
c=json.loads((ROOT/'results/calibration_direct.json').read_text())

def job(a,d):
    name=f'full_a{a}_d{d}'
    result=ROOT/'results'/f'{name}.json'
    if result.exists():return json.loads(result.read_text())
    return run(name,amp=a,duty=d/100,pot=c[str(a)]['pot_top_ohm'],split=10000,cap=47e-12,full=True)

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(job,a,d) for a in [4,1,2,3] for d in [10,30,50]]
        results=[j.result() for j in jobs]
    # Matplotlib figures are generated sequentially.
    for r in results:assess(r['name'])
    (ROOT/'results/full_matrix_index.json').write_text(json.dumps([r['name'] for r in results],indent=2))
