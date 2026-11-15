"""Selected-candidate numerical and range checks; independent saved runs."""
import json
from concurrent.futures import ThreadPoolExecutor
from alt2 import ROOT,run
from edges import assess
c=json.loads((ROOT/'results/calibration_direct.json').read_text())
base=dict(amp=4,pot=c['4']['pot_top_ohm'],split=10000,cap=47e-12,full=True)
cases=[('fine_a4_d50_h025',{'duty':.5,'step':.25}),
       ('fine_a4_d50_h0125',{'duty':.5,'step':.125}),
       ('fine_a4_d10_h0125',{'duty':.1,'step':.125}),
       ('full_span_high_d10',{'duty':.1,'pot':500})]
def job(case):
    name,kw=case
    return run(name,**(base|kw))
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(job,cases))
    for r in results:assess(r['name'])
