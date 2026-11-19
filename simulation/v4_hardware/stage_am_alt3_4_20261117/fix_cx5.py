"""Run the three _cx5 detuning corners with the corrected SI unit handling."""
import json
from concurrent.futures import ProcessPoolExecutor

from reanalyse import job_from_metrics

NAMES = ['h90_332_cx5', 'h90_392_cx5', 'h90_472_cx5']


def one(n):
    import engine as e
    j = json.load(open('joint/%s_metrics.json' % n, encoding='utf-8'))
    job = job_from_metrics(j)
    o = e.run(job, force=True)
    return n, o['P_rad_mW'], o['I_rad_carrier_mA'], o['port_Z31'], o['energy_closure']['relative_error']


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as ex:
        for n, p, i, z, c in ex.map(one, NAMES):
            print('%-16s Prad %.6f mW  Irad %.4f mA  Im(Z)=%+.2f  closure %+.2e'
                  % (n, p, i, z[1], c), flush=True)
