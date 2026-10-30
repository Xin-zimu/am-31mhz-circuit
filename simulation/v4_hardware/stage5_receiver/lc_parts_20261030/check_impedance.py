"""S05-08: impedance / matching risk, deliberately separated from tuning.

Tuning to 31 MHz says nothing about a 50 ohm interface. This script reports
what the network actually presents, and what happens when the source is not
50 ohm, without adopting a matching network into the baseline.
"""
from pathlib import Path
import json, sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lc_parts as LP
import check_models as CM

AC = json.loads((HERE/'ac_cases.json').read_text(encoding='utf-8'))
PAR = {row['name']: row['parameters'] for row in AC}
n = LP.LoadedNetwork()


def zin(p, f=31e6):
    _, z = LP.response(n, p, f=np.array([float(f)]))
    return complex(z[0])


def swr(z, z0=50.0):
    g = abs((z-z0)/(z+z0))
    return float(-20*np.log10(g)), float((1+g)/(1-g)), float(g)


rows = []
for name in ('NOM_132', 'Q_PESS40', 'Q_OPT80', 'CT_Q200', 'IRF24_Q40',
             'TOL_0p95_0p95', 'TOL_1p05_1p05', 'MATCH_CSEL'):
    p = PAR[name]
    z31 = zin(p)
    rl, vswr, g = swr(z31)
    # sweep the source resistance to show that "tuned" is not "matched"
    src = {}
    for rs in (25.0, 50.0, 100.0, 200.0):
        q = dict(p, rs=rs)
        h, zq = LP.response(n, q)
        m = LP.metrics(n.f, h, zq)
        src[str(rs)] = dict(gain31_v_v=float(m['gain31_v_v']),
                            gain31_db=float(m['gain31_db']),
                            center_edges_mhz=float(m['center_edges_mhz']),
                            bw_mhz=float(m['bw_mhz']),
                            relative29_db=float(m['relative29_db']),
                            relative33_db=float(m['relative33_db']))
    rows.append(dict(case=name, zin31=[z31.real, z31.imag], return_loss_db=rl,
                     vswr=vswr, gamma=g, source_sweep=src,
                     note='return loss is referenced to 50 ohm; it is NOT an antenna match'))

# reflection across the band for the nominal board
p = PAR['NOM_132']
f = np.linspace(28e6, 34e6, 241)
_, z = LP.response(n, p, f=f)
gam = np.abs((z-50)/(z+50))
band = dict(f_mhz=[float(x/1e6) for x in f],
            return_loss_db=[float(-20*np.log10(g)) for g in gam])

json.dump(dict(rows=rows, band=band,
               definition='Zin = Rs*Vin/(Vsrc-Vin); return loss = -20log10|(Zin-50)/(Zin+50)|',
               warning='a 50 ohm source in the fixture is a test condition, not the antenna'),
          open(HERE/'impedance.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

for r in rows:
    print(r['case'], 'Zin=%.1f%+.1fj' % tuple(r['zin31']),
          'RL=%.2f dB' % r['return_loss_db'], 'VSWR=%.2f' % r['vswr'])
print('source sweep @31 MHz, nominal:',
      {k: round(v['gain31_db'], 3) for k, v in rows[0]['source_sweep'].items()})
