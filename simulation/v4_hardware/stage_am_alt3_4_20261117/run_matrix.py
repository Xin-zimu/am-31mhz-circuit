"""Run the AM-ALT.3.4 candidate matrix through the frozen driver.

Usage:
    py -3 run_matrix.py            # everything that is not already computed
    py -3 run_matrix.py base       # only the three principal 90 cm candidates
    py -3 run_matrix.py corners    # only the corner cases

Each case is a separate ngspice process, and the processes are run in a small
pool (default 6) because this machine has 28 logical cores.  Results are
cached per case: an existing .raw is reused only when the generated netlist
text is byte-identical to the one on disk.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import candidates as cand

HERE = Path(__file__).resolve().parent
OUT = HERE / 'joint'


def _one(job):
    import engine as e
    t = time.time()
    try:
        o = e.run(job)
        return dict(ok=True, name=job['name'], secs=time.time() - t,
                    text=e.line(o), eta_b=o['eta_battery_to_rad_pct'],
                    eta_m=o['eta_match_to_rad_pct'], prad=o['P_rad_mW'],
                    closure=o['energy_closure']['relative_error'])
    except Exception as exc:                       # noqa: BLE001
        return dict(ok=False, name=job['name'], secs=time.time() - t,
                    error='%s: %s' % (type(exc).__name__, exc))


GROUPS = {
    'base': cand.make(cand.BASE_CASES),
    'family': cand.make(cand.FAMILY_CASES),
    'secondary': cand.make(cand.SECONDARY_CASES),
    'corners': cand.make(cand.CORNER_CASES),
    'ceiling': cand.make(cand.CEILING_CASES),
}


def main(argv):
    which = argv[1:] or ['base', 'secondary', 'corners']
    jobs = []
    for g in which:
        if g not in GROUPS:
            raise SystemExit('unknown group %r; choose from %s' % (g, list(GROUPS)))
        jobs += GROUPS[g]
    print('cases: %d' % len(jobs), flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=min(6, len(jobs))) as ex:
        futs = {ex.submit(_one, j): j for j in jobs}
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            if r['ok']:
                print('[%6.1fs] %s' % (r['secs'], r['text']), flush=True)
            else:
                print('[%6.1fs] %s FAILED %s' % (r['secs'], r['name'], r['error']), flush=True)
    bad = [r for r in results if not r['ok']]
    (HERE / 'run_matrix_last.json').write_text(json.dumps(results, indent=1), encoding='utf-8')
    print('done: %d ok, %d failed' % (len(results) - len(bad), len(bad)), flush=True)
    if bad:
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv)
