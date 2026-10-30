"""S05-08: full-chain transient with purchasable-part LC models.

Reuses the S05-06 warm-bias recipe verbatim (unforced OPA DC solve + detector
mean), only the front-end netlist and its directory change.  Every case lands
in this folder; nothing in gain_20261030 is rewritten.
"""
from pathlib import Path
import sys, json, time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lc_parts as LP
import check_models as CM

sys.path.insert(0, str(HERE.parent/'gain_20261030'))
import run_gain as G
# run_gain imported run_diagnosis with the S05-06 paths baked in; redirect every
# writer to this stage so no historical record or netlist can be overwritten.
G.HERE = HERE
G.WORK = Path('D:/ms_xsp/s05_parts_tran_20261030')
G.d.HERE = HERE
G.d.WORK = G.WORK
G.d.EXE = G.d.old.EXE
fixed, sha = G.fixed, G.sha

CASES = {}


def register(name, params, k=0.0):
    """Write the front-end netlist for one LC condition and remember its path."""
    fp = HERE/'filters'/(name+'.cir')
    fixed(fp, CM.filter_text(params, k).encode('ascii'))
    CASES[name] = dict(path=str(fp), params=params, mutual_k=k)
    return str(fp)


def seeded(name, front, **kw):
    """S05-06 'seeded' recipe with an explicit front-end file."""
    c = G.cfg(front_file=front, **kw)
    op, opr = G.probe('P_G'+str(1+c['feedback']/10000).replace('.', 'p')+'_noic',
                      feedback=c['feedback'])
    rc = dict(c); rc.update(start=100, stop=200, load=1e15)
    rfraw, rfr = G.rf(name+'_RFopen', **rc)
    mean = rfr['metrics']['nodes']['out']['dc']
    net = (G.d.circuit(c, G.d.source(c))
           + G.d.old.old.detector(dict(dc_return='direct', rd=4700, cd=100, rf=4700, cf=100, load=1e15))
           + G.d.old.old.models() + G.bb(c))
    net += f'.ic v(out)={mean:.16g} v(bbin)=3 v(ref)=3\n'
    net += ''.join(f'.nodeset {k}={float(v[0]):.16g}\n' for k, v in op.items()
                   if k.startswith('v(xopa.') or k in ['v(bbo)', 'v(neg)'])
    raw, r = G.wrapper(name, net,
                       f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n",
                       c, G.d.SAVES+' v(bbin) v(ref) v(bbo) v(final)')
    r['initialization'] = dict(kind='internal model nodeset from unforced OP; capacitor prebias '
                                    'at detector mean', detector_mean=mean, not_cold_start=True)
    r['front_end'] = CASES.get(Path(c['front_file']).stem, {})
    r['metrics'] = G.metrics(raw, c)
    if c['stop']-c['start'] >= 50:
        r['rf_metrics'] = G.d.measure(raw, c)
    G.d.save(r)
    print(json.dumps({'name': name, 'final': r['metrics']['final'], 'elapsed': r['elapsed_s']}),
          flush=True)
    return raw, r
