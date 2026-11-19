"""Rebuild metrics from every cached .raw, serially, with explicit assertions.

Serial on purpose: an earlier attempt ran the pool twice against the same case
names, two ngspice processes raced on the same .raw file and the whole batch had
to be thrown away. One process at a time cannot do that.
"""
import glob
import json
import os
import sys

import engine as e
from reanalyse import job_from_metrics


def main():
    names = sorted(os.path.basename(p).replace('_metrics.json', '') for p in glob.glob('joint/*_metrics.json'))
    print('rebuilding %d cases' % len(names), flush=True)
    bad = []
    for n in names:
        mp = 'joint/%s_metrics.json' % n
        if os.path.exists(mp):
            job = job_from_metrics(json.load(open(mp, encoding='utf-8')))
        else:
            raise SystemExit('no metrics template for %s' % n)
        before = dict(job)
        try:
            txt, d = e.netlist(job)
            raw = e.OUT / (n + '.raw')
            cir = e.OUT / (n + '.cir')
            if not raw.exists() or not cir.exists():
                raise RuntimeError('missing raw/cir; reconstruct before reanalysis')
            if e._electrical(cir.read_text(encoding='utf-8')) != e._electrical(txt):
                raise RuntimeError('cached netlist differs; explicit simulation required')
            o = e.analyse(job, d)
        except Exception as exc:            # noqa: BLE001
            bad.append((n, '%s: %s' % (type(exc).__name__, exc)))
            print('  FAILED', n, exc, flush=True)
            continue
        after = json.load(open(mp, encoding='utf-8'))['assumptions']
        expect_contact = 2.0 if '_ct2' in n else 0.2
        expect_cbase = 2.0 if '_cb2' in n else 0.5
        if abs(after['contact_ohm'] - expect_contact) > 1e-9:
            bad.append((n, 'contact drifted to %s' % after['contact_ohm']))
        if abs(after['cbase_pF'] - expect_cbase) > 1e-9:
            bad.append((n, 'cbase drifted to %s' % after['cbase_pF']))
        print('  %-20s Prad %.6f mW  closure %+.2e' %
              (n, o['P_rad_mW'], o['energy_closure']['relative_error']), flush=True)
    print('done, %d problems' % len(bad))
    for b in bad:
        print('  ', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
