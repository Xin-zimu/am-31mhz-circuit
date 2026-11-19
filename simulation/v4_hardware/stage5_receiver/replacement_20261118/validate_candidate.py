"""Isolated 470 nH / G40-G44 receiver study; retains historical fixtures.

The RF input is an assumed 50-ohm Thevenin source derived from the previous
link estimate, not an antenna measurement. Warm initialisation is reused from
S05-08 and must not be described as cold-start validation.
"""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent
HERE = ROOT / 'bourns'
STAGE = ROOT.parent
sys.path.insert(0, str(STAGE / 'lc_parts_20261030'))
import lc_parts as LP
import check_models as CM
sys.path.insert(0, str(STAGE / 'gain_20261030'))
import run_gain as G

G.HERE = HERE
G.WORK = Path('D:/ms_xsp/s05_replacement_bourns_20261118')
G.d.HERE = HERE
G.d.WORK = G.WORK
CM.HERE = HERE
CM.d.HERE = HERE
CM.d.WORK = G.WORK
TX = json.loads((STAGE.parent / 'stage_am_alt3_4_20261117/joint/h90_332_metrics.json').read_text())
MOD = TX['modulation_index']
# Historical coefficient: 0.4777 Vpp per mV at m=0.5, G22.
RF_VPK = TX['V2_est_Vpp'] / (0.4777 * MOD / 0.5) * 1e-3
LP.PARTS['78FR47K-RC'] = dict(l_nh=470, tol=.10, q_ref=40, f_ref=25e6,
                              srf_mhz=270, dcr_ohm=.11)


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                       allow_nan=False) + '\n', encoding='utf-8')


def prepare():
    """Fit nominal and tolerance corners; explicitly record capacitor changes."""
    (HERE / 'filters_v2').mkdir(parents=True, exist_ok=True)
    # Recreate the archived AC fixture locally: its external raw cache is gone.
    original = (STAGE / 'gain_20261030/netlists/C_Q50.cir').read_text()
    old_record = json.loads((STAGE / 'gain_20261030/results/C_Q50.json').read_text())
    original = original.replace(old_record['raw_path'].replace('\\', '/'), '@RAW@')
    raw, record = G.d.execute('port_ac_recreated', original, dict(kind='archived C_Q50 AC rerun'))
    G.d.save(record)
    f = raw['frequency'].real
    n = SimpleNamespace(f=f, ref=raw['v(rf)'],
                        yload=2j*np.pi*f*10.81e-12*(raw['v(tank2)']-raw['v(port)'])/raw['v(port)'],
                        amp=raw['v(rf)']/raw['v(port)'])
    rows = []
    for name, l1, l2, q, cq in [
        ('nominal', 470, 470, 40, 400),
        ('low_low', 423, 423, 40, 400),
        ('low_high', 423, 517, 40, 400),
        ('high_low', 517, 423, 40, 400),
        ('high_high', 517, 517, 40, 400),
        ('loss_stress', 470, 470, 25, 200),
    ]:
        p = LP.default_params(part='78FR47K-RC', l1=l1, l2=l2, q31=q, ct_q=cq,
                              ct1=37.5*470/l1, ct2=44.8*470/l2)
        bounds = {key: (p[key]-6, p[key]+6) for key in ('ct1', 'ct2')}
        p, opt = CM.tune(n, p, bounds=bounds)
        h, z = LP.response(n, p)
        fixed = {}
        for i in (1, 2):
            possibilities = [(abs(p[f'ct{i}'] - v - 10), v, p[f'ct{i}'] - v)
                             for v in (18, 22, 27, 30, 33, 39, 47, 51, 56, 62)
                             if 2 <= p[f'ct{i}'] - v <= 18]
            _, base, trim = min(possibilities)
            fixed[str(i)] = dict(fixed_pf=base, trim_pf=trim)
        print('TUNING', name, p['ct1'], p['ct2'], 'peak', LP.FGRID[np.argmax(abs(h))], flush=True)
        rows.append(dict(name=name, parameters=p, fit=opt,
                         analytic=LP.metrics(LP.FGRID, h, z), capacitors=fixed,
                         historical_30_39_pf_fit=bool(32 <= p['ct1'] <= 48
                                                       and 41 <= p['ct2'] <= 57)))
        G.fixed(HERE / 'filters_v2' / (name + '.cir'), CM.filter_text(p).encode('ascii'))
    dump('tuning.json', rows)
    return rows


def run_case(name, front, feedback, duty, modulation, step=0.5):
    """Run actual RF stages, BAT85, and TI OPA197 macro with warm prebias."""
    c = G.cfg(front_file=str(front), feedback=feedback, wave='square',
              duty=duty, ac=RF_VPK, m=modulation, step=step,
              start=150, stop=450, timeout_s=360 if step < .5 else 180)
    op, _ = G.probe('P_G' + str(int(1 + feedback / 10000)), feedback=feedback)
    rc = dict(c)
    rc.update(start=100, stop=200, load=1e15)
    _, rr = G.rf(name + '_RFopen', **rc)
    mean = rr['metrics']['nodes']['out']['dc']
    net = (G.d.circuit(c, G.d.source(c))
           + G.d.old.old.detector(dict(dc_return='direct', rd=4700, cd=100,
                                      rf=4700, cf=100, load=1e15))
           + G.d.old.old.models() + G.bb(c))
    net += f'.ic v(out)={mean:.16g} v(bbin)=3 v(ref)=3\n'
    net += ''.join(f'.nodeset {k}={float(v[0]):.16g}\n' for k, v in op.items()
                   if k.startswith('v(xopa.') or k in ['v(bbo)', 'v(neg)'])
    raw, r = G.wrapper(name, net,
                      f"tran {step}n {c['stop']}u {c['start']}u {step}n",
                      c, G.d.SAVES + ' v(bbin) v(ref) v(bbo) v(final)')
    r['initialization'] = dict(kind='warm capacitor prebias and OPA nodesets',
                               not_cold_start=True, detector_mean=mean)
    r['metrics'] = G.metrics(raw, c)
    r['rf_input_assumption'] = dict(thevenin_peak_v=RF_VPK, resistance_ohm=50,
                                   modulation=modulation, not_measured=True)
    G.d.save(r)
    print(json.dumps(dict(name=name, final=r['metrics']['final']), ensure_ascii=False), flush=True)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', action='store_true')
    args = ap.parse_args()
    tuning = prepare()
    for row in tuning:
        row['spice'] = CM.spice('AC_' + row['name'], row['parameters'])
        row['gain_error_db'] = row['spice']['gain31_db'] - row['analytic']['gain31_db']
    dump('ac_verified.json', tuning)
    front = HERE / 'filters_v2/nominal.cir'
    jobs = [('G40_D50', front, 390000, .5, MOD, .5)]
    if not args.pilot:
        for gain, fb, duties in [(22, 210000, (.5,)), (44, 430000, (.1, .3, .5))]:
            for duty in duties:
                name = f'G{gain}_D{round(100*duty)}'
                if name != 'G40_D50':
                    jobs.append((name, front, fb, duty, MOD, .5))
        for duty in (.1, .5):
            jobs.append((f'G44_D{round(100*duty)}_half', front, 430000, duty, MOD / 2, .5))
        jobs.append(('G44_D50_fine_retry', front, 430000, .5, MOD, .25))
        jobs.append(('G44_D50_loss', HERE / 'filters_v2/loss_stress.cir', 430000, .5, MOD, .5))
    rows = []
    G.init()
    for gain, fb in [(22, 210000), (40, 390000), (44, 430000)]:
        G.probe('P_G' + str(gain), feedback=fb)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_case, *job) for job in jobs]
        for future in as_completed(futures):
            r = future.result()
            rows.append(dict(name=r['name'], config=r['config'], metrics=r['metrics'],
                             net_sha256=r['net_sha256'], raw_sha256=r['raw_sha256'],
                             elapsed_s=r['elapsed_s']))
            dump('summary.json', dict(rf_peak_v=RF_VPK, modulation=MOD,
                                     not_wireless_qualification=True, rows=rows))
    print('COMPLETED', len(rows), flush=True)


if __name__ == '__main__':
    main()
