"""S05-09: how much does the probe itself move the network it measures?

A passive 10:1 probe is typically 10-15 pF in parallel with 1-10 MOhm. On a
2.4 pF coupling capacitor and a 46 pF tank that is not a small perturbation.
This uses the S05-08 analytic solver (validated to 1e-13 against ngspice) so no
new SPICE run is needed; the numbers are design guidance for the bench, not
measurements.
"""
from pathlib import Path
import json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lc_parts_20261030'))
import lc_parts as LP

HERE = Path(__file__).resolve().parent
PARTS = Path(__file__).resolve().parents[1]/'lc_parts_20261030'
AC = json.loads((PARTS/'ac_cases.json').read_text(encoding='utf-8'))
NOM = next(r for r in AC if r['name'] == 'NOM_132')['parameters']
n = LP.LoadedNetwork()

PROBES = [
    ('none', 0.0),
    ('active/1pF', 1.0),
    ('10:1 low-cap 3pF', 3.0),
    ('typical 10:1 10pF', 10.0),
    ('cheap 10:1 15pF', 15.0),
]

def measure(extra_pf_tank1, extra_pf_tank2=0.0):
    p = dict(NOM)
    p['board1'] = NOM['board1'] + extra_pf_tank1
    p['board2'] = NOM['board2'] + extra_pf_tank2
    h, z = LP.response(n, p)
    m = LP.metrics(n.f, h, z)
    return dict(gain31=m['gain31_v_v'], center=m['center_edges_mhz'],
                bw=m['bw_mhz'], d29=m['relative29_db'], d33=m['relative33_db'])

rows = []
for label, c in PROBES:
    on_tank1 = measure(c)
    on_tank2 = measure(0.0, c)
    rows.append(dict(probe=label, cap_pf=c,
                     on_tank1=on_tank1, on_tank2=on_tank2,
                     bw_error_pct_tank2=100*(on_tank2['bw']-measure(0,0)['bw'])/measure(0,0)['bw']))

base = measure(0.0, 0.0)
out = dict(baseline=base, probes=rows,
           note=('probe capacitance is added to the tank node it touches; a probe on '
                 'tank2 is shown separately because the S05-07 sweep found tank2 the '
                 'more sensitive node'),
           advice=('do not probe tank1/tank2 directly; measure at the buffered RF node '
                   'whose 1 kOhm load swamps the probe, and record the probe R/C in the '
                   'log'))
json.dump(out, open(HERE/'probe_loading.json', 'w', encoding='utf-8'), indent=2)

print('%-20s %8s %10s %9s %9s %9s' % ('probe', 'C/pF', 'G31', 'centre', 'BW', 'BW err%'))
for r in rows:
    t = r['on_tank2']
    print('%-20s %8.1f %10.3f %9.4f %9.4f %+9.2f' %
          (r['probe'], r['cap_pf'], t['gain31'], t['center'], t['bw'], r['bw_error_pct_tank2']))
print()
print('baseline BW %.4f MHz, 29/33 dB %.2f/%.2f' % (base['bw'], base['d29'], base['d33']))
