"""Re-simulate only the cases whose netlist genuinely changed.

Currently: the six L+-5 % detuning corners and the three cases whose .raw was
lost.  Everything else reuses its cache.
"""
import json
from concurrent.futures import ProcessPoolExecutor

from reanalyse import job_from_metrics

NAMES = ['h90_332_Lm5', 'h90_332_Lp5', 'h90_392_Lm5', 'h90_392_Lp5',
         'h90_472_Lm5', 'h90_472_Lp5', 'h90_332', 'h100_332', 'h100_472']


def one(n):
    import engine as e
    j = json.load(open('joint/%s_metrics.json' % n, encoding='utf-8'))
    job = job_from_metrics(j)
    if n.endswith(('_Lm5', '_Lp5')):
        job['retune'] = False
    o = e.run(job)
    return n, o['P_rad_mW'], o['I_rad_carrier_mA'], o['port_Z31'][1], o['energy_closure']['relative_error']


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=5) as ex:
        for n, p, i, z, c in ex.map(one, NAMES):
            print('%-16s Prad %.6f mW  Irad %.4f mA  Im=%+8.2f  closure %+.2e'
                  % (n, p, i, z, c), flush=True)
