"""S05-08: real-part AC models, retuning, tuning range and matching risk.

The analytic MNA solve drives the search; every reported case is then re-solved
by the full original RF active stage in ngspice.  No transient here.
"""
from pathlib import Path
import json, sys
import numpy as np
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lc_parts as LP

STAGE = HERE.parent
sys.path.insert(0, str(STAGE/'blocker_20261029'))
import run_diagnosis as d
d.HERE = HERE
d.WORK = Path('D:/ms_xsp/s05_parts_20261030')
fixed, sha = d.fixed, d.sha

FIT = np.array([29, 30, 30.5, 30.8, 31, 31.2, 31.5, 32, 33])*1e6
# Physical tuning window of the proposed board:
#   tank1  30 pF C0G + 2..18 pF trimmer  -> 32..48 pF total
#   tank2  39 pF C0G + 2..18 pF trimmer  -> 41..57 pF total
CT_BOUNDS = dict(ct1=(32.0, 48.0), ct2=(41.0, 57.0))


def dump(path, value):
    fixed(path, (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8'))


# ------------------------------------------------------------------ netlist
def filter_text(p, k=0.0, frozen=31e6):
    t = '* S05-08 purchasable-part loaded fixture; original active stages unchanged\n'
    t += f"CSEL input tank1 {p['cs']:.12g}p\nCK tank1 tank2 {p['ck']:.12g}p\n"
    t += f"COUT tank2 port {p['co']:.12g}p\nRPORT port 0 1Meg\n"
    for i in (1, 2):
        Lnh = p[f'l{i}']
        r = float(LP.series_r(frozen, p, i))
        cp = LP.coil_cp_pf(p['part']) if p.get(f'cp{i}') is None else p[f'cp{i}']
        ct = p[f'ct{i}']+p[f'board{i}']
        if p['ct_q']:
            t += f"RCT{i} tank{i} ctl{i} {1/(2*np.pi*31e6*ct*1e-12*p['ct_q']):.12g}\n"
            t += f"CTUNE{i} ctl{i} 0 {ct:.12g}p\n"
        else:
            t += f"CTUNE{i} tank{i} 0 {ct:.12g}p\n"
        t += f"RLOSS{i} tank{i} ln{i} {r:.12g}\nLSEL{i} ln{i} 0 {Lnh:.12g}n\n"
        t += f"CSELF{i} tank{i} 0 {cp:.12g}p\n"
    if k:
        t += f"KSTRAY LSEL1 LSEL2 {k:.12g}\n"
    return t


def spice(name, p, k=0.0):
    fp = HERE/'filters'/(name+'.cir')
    fixed(fp, filter_text(p, k).encode('ascii'))
    raw, r = d.ac(name, front_file=str(fp), rs=p['rs'])
    f = raw['frequency'].real
    z = p['rs']*raw['v(input)']/(1-raw['v(input)'])
    m = LP.metrics(f, raw['v(rf)'], z)
    dump(HERE/'results'/(name+'_measured.json'),
         dict(parameters=p, mutual_k=k, metrics=m, kind='ngspice AC, full RF active stage'))
    return m


# ------------------------------------------------------------------- tuning
def tune(n, p, matching=False, bounds=None, k=0.0):
    """Capacitor fit to the archived A relative shape; optional 50 ohm term."""
    target = 20*np.log10(abs(np.interp(FIT, n.f, n.ref))/abs(np.interp(31e6, n.f, n.ref)))
    keys = ['ct1', 'ct2']+(['cs'] if matching else [])
    default = dict(CT_BOUNDS); default['cs'] = (8.0, 30.0)
    lo, hi = zip(*[(bounds or default)[key] for key in keys])
    def fun(x):
        h, z = LP.response(n, {**p, **dict(zip(keys, x))}, FIT, k=k)
        err = 20*np.log10(abs(h)/abs(h[4]))-target
        if matching:
            gam = (z[4]-50)/(z[4]+50)
            err = np.r_[err, 8*gam.real, 8*gam.imag]
        return err
    r = least_squares(fun, [p[key] for key in keys], bounds=(list(lo), list(hi)),
                      xtol=1e-11, ftol=1e-11, gtol=1e-11, max_nfev=200)
    return ({**p, **{key: float(v) for key, v in zip(keys, r.x)}},
            dict(success=bool(r.success), nfev=int(r.nfev), cost=float(r.cost),
                 parameters=keys, bounds={key: list((bounds or default)[key]) for key in keys}))


def at_bounds(p, bounds=None):
    out = {}
    for key, (lo, hi) in (bounds or CT_BOUNDS).items():
        if key in p:
            out[key] = bool(min(abs(p[key]-lo), abs(p[key]-hi)) < 1e-3)
    return out


# --------------------------------------------------------------- case list
def main():
    n = LP.LoadedNetwork()

    models = {}
    for key in LP.PARTS:
        pa = LP.PARTS[key]
        entry = dict(part=key, label=pa['label'], l_nh=pa['l_nh'], tol=pa['tol'],
                     srf_mhz=pa['srf_mhz'], dcr_ohm=pa['dcr_ohm'],
                     cp_from_srf_pf=LP.coil_cp_pf(key), evidence=pa['evidence'],
                     source=pa['source'], q_vs_beta={})
        for beta in (0.0, 0.25, 0.5, 0.75, 1.0):
            q = LP.q_at(31e6, key, pa['l_nh'], beta)
            entry['q_vs_beta'][str(beta)] = dict(
                q31=q, r31_ohm=2*np.pi*31e6*pa['l_nh']*1e-9/q,
                r_test_freq_ohm=float(LP.coil_r(key, pa['f_ref'], beta)))
        models[key] = entry
    models['BFC280905003'] = dict(LP.CT_MODEL)
    dump(HERE/'part_models.json', models)

    # solver cross-check: 8-node MNA with R(f) and k=0 vs run_lc four-node
    probe = dict(l1=460., l2=460., q1=50., q2=50., cp1=LP.coil_cp_pf('132-17L'),
                 cp2=LP.coil_cp_pf('132-17L'), ct1=40.37920912906399,
                 ct2=46.31557312225309, cs=15., co=11., ck=2.4, rs=50.,
                 coil='constant_esr', board1=1., board2=1.)
    hr, zr = n.response(probe)
    hm, zm = LP.response(n, LP.default_params(q31=50.0), k=0.0, frozen_r=False)
    mr = LP.metrics(n.f, hr, zr)
    dump(HERE/'solver_crosscheck.json', dict(
        note='run_lc four-node analytic (S05-07) vs S05-08 eight-node MNA at k=0',
        max_relative_signal_error=float(np.max(np.abs(hm/hr-1))),
        max_relative_impedance_error=float(np.max(np.abs(zm/zr-1))),
        reference_metrics=mr))

    rows = []

    def add(name, p, k=0.0, verify=True, optimization=None, note=None, frozen_r=True,
            **extra):
        h, z = LP.response(n, p, k=k, frozen_r=frozen_r)
        row = dict(name=name, parameters=p, mutual_k=k, note=note,
                   analytic=LP.metrics(n.f, h, z))
        row.update(extra)
        if optimization is not None:
            row['optimization'] = optimization
        if verify:
            row['spice'] = spice(name, p, k)
            row['spice_minus_analytic_db'] = row['spice']['gain31_db']-row['analytic']['gain31_db']
        rows.append(row)
        return row

    # frozen-R approximation bracket on the nominal design
    nom_src = LP.default_params(beta=0.5, ct_q=1290.0)
    nom, opt = tune(n, nom_src)
    add('NOM_132', nom, optimization=opt, ct_at_bound=at_bounds(nom),
        note='datasheet beta=0.5 (Q31~72.9), Cp from SRF bound, trimmer at the '
             'optimistic end of its own tan-d range')
    add('NOM_132_Rfreq', nom, verify=False, frozen_r=False,
        note='analytic only: series R follows beta across the sweep instead of being '
             'frozen at 31 MHz; bounds the approximation used by every SPICE fixture')

    for name, p in [
            ('Q_FLOOR66', LP.default_params(beta=0.5, q31=66.0, ct_q=1290.0)),
            ('Q_OPT80',   LP.default_params(beta=0.0, q31=80.0, ct_q=1290.0)),
            ('Q_PESS40',  LP.default_params(beta=1.0, q31=40.0, ct_q=1290.0)),
            ('CT_Q400',   LP.default_params(beta=0.5, ct_q=400.0)),
            ('CT_Q200',   LP.default_params(beta=0.5, ct_q=200.0))]:
        q, op = tune(n, p)
        add(name, q, optimization=op, ct_at_bound=at_bounds(q))

    # board stray: design tuned with 1 pF/tank, then +1 pF/tank appears
    stray = dict(nom, board1=2.0, board2=2.0)
    add('STRAY_p1p', stray, note='design capacitors held; one extra pF per tank')
    q, op = tune(n, LP.default_params(beta=0.5, ct_q=1290.0, board1=2.0, board2=2.0))
    add('STRAY_p1p_RETUNED', q, optimization=op, ct_at_bound=at_bounds(q))

    # coil-to-coil mutual coupling: stress bracket, both signs
    for tag, k in [('m03', -0.03), ('p03', 0.03)]:
        add('MUT_'+tag, nom, k=k,
            note='tuned at k=0 then evaluated with coupling')
        q, op = tune(n, nom, k=k)
        add(f'MUT_{tag}_RETUNED', q, k=k, optimization=op, ct_at_bound=at_bounds(q))

    # inductance tolerance corners
    for s1, s2 in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        p = LP.default_params(beta=0.5, ct_q=1290.0, l1=460*(1+.05*s1), l2=460*(1+.05*s2))
        tag = 'TOL_' + f'{1+.05*s1:.2f}'.replace('.', 'p') + '_' + f'{1+.05*s2:.2f}'.replace('.', 'p')
        add(tag+'_HELD', p, note='same capacitors as NOM; only the inductance moved')
        q, op = tune(n, p)
        add(tag, q, optimization=op, ct_at_bound=at_bounds(q))

    # alternative inductor and forced source impedance
    irf = LP.default_params(part='IRF-24', l1=470.0, l2=470.0, q31=40.0, ct_q=1290.0)
    q, op = tune(n, irf)
    add('IRF24_Q40', q, optimization=op, ct_at_bound=at_bounds(q))
    add('NOM_RS200', dict(nom, rs=200.0), note='forced source impedance, not an antenna')

    # matching exploration: release CSEL, take the reflection term into the fit
    q, op = tune(n, nom_src, matching=True)
    add('MATCH_CSEL', q, optimization=op,
        note='CSEL released to reduce |Gamma|; NOT adopted into the baseline')

    dump(HERE/'ac_cases.json', rows)
    print(json.dumps({r['name']: {key: round(r['analytic'][key], 4) for key in
          ('gain31_v_v', 'center_edges_mhz', 'bw_mhz', 'relative29_db',
           'relative33_db', 'return_loss50_db')} for r in rows}, indent=1))


if __name__ == '__main__':
    main()
