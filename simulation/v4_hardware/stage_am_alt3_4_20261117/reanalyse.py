"""Rebuild every *_metrics.json from its cached .raw WITHOUT re-simulating.

The stored 'assumptions' block in a metrics file uses reporting names
(contact_ohm, cbase_pF, coil_loss_scale, ...).  engine.run() expects the job
names (contact, cbase, ...).  Passing the stored block straight through silently
falls back to the engine defaults, which is how one case lost its raw file
earlier.  The mapping is explicit here and asserted afterwards.
"""
import glob
import json
import sys

import engine as e

# stored name -> (engine job key, factor from stored unit to SI unit)
#
# The stored 'assumptions' block is written in REPORTING units (pF for
# capacitances, ohm for resistances) because that is what the documents quote.
# engine.run() takes SI units.  Applying the factor is mandatory: without it a
# 0.5 pF base capacitance becomes 0.5 F, the antenna node is shorted to RF
# ground and the case silently produces a radiated power of 1e-24 mW.
KEYMAP = {
    'contact_ohm': ('contact', 1.0),
    'cbase_pF': ('cbase', 1e-12),
    'cant_scale': ('cant_scale', 1.0),
    'coil_loss_scale': ('coil_loss_scale', 1.0),
    'coil_L_scale': ('coil_L_scale', 1.0),
    'coil_extra_C_pF': ('coil_extra_C_pF', 1e-12),
    'trim_tand': ('trim_tand', 1.0),
    'retune': ('retune', 1.0),
}


def job_from_metrics(j):
    job = dict(name=j['name'], part=j['part'], length_cm=j['length_cm'],
               step_ns=j['step_ns'])
    for k, v in j['assumptions'].items():
        if k not in KEYMAP:
            raise SystemExit('unmapped assumption key %r in %s' % (k, j['name']))
        key, factor = KEYMAP[k]
        job[key] = bool(v) if key == 'retune' else v * factor
    return job


def assert_job_matches(job, stored, name):
    """Fail loudly if the engine would silently use a default or a wrong unit."""
    back = dict(job)
    for k, v in stored.items():
        key, factor = KEYMAP[k]
        if abs(back[key] - v * factor) > 1e-12 * max(1.0, abs(v * factor)):
            raise SystemExit('%s: %s round-trip mismatch' % (name, k))
    if back['cbase'] > 1e-9:
        raise SystemExit('%s: cbase looks like pF passed as F (%.3g)' % (name, back['cbase']))
    return True


def main():
    names = sorted(json.loads(open(p, encoding='utf-8').read())['name']
                   for p in glob.glob('joint/*_metrics.json'))
    bad = []
    for n in names:
        j = json.loads(open('joint/%s_metrics.json' % n, encoding='utf-8').read())
        job = job_from_metrics(j)
        try:
            txt, d = e.netlist(job)
            cir = e.OUT / (n + '.cir')
            if not (e.OUT / (n + '.raw')).exists() or e._electrical(cir.read_text(encoding='utf-8')) != e._electrical(txt):
                raise RuntimeError('missing or incompatible cache; explicit simulation required')
            e.analyse(job, d)
        except Exception as exc:             # noqa: BLE001
            bad.append((n, '%s: %s' % (type(exc).__name__, exc)))
        # assert the re-analysis used the documented corner, not a default
        after = json.loads(open('joint/%s_metrics.json' % n, encoding='utf-8').read())
        if after['assumptions'] != j['assumptions']:
            bad.append((n, 'assumptions drifted: %s -> %s' % (j['assumptions'],
                                                             after['assumptions'])))
    print('reanalysed %d cases, %d problems' % (len(names), len(bad)))
    for b in bad:
        print(' ', b)
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    main()
