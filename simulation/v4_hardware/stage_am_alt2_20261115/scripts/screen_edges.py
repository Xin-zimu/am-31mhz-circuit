import json
from alt2 import ROOT,run
from edges import assess
c=json.loads((ROOT/'results/calibration_direct.json').read_text())
for cap in [22,47,100,220]:
    name=f'edge_c{cap}p_d10'
    run(name,amp=4,duty=.1,pot=c['4']['pot_top_ohm'],split=10000,cap=cap*1e-12)
    assess(name)
