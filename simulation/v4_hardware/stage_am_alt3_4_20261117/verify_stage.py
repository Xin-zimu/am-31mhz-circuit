"""Independent checks for AM-ALT.3.4. Nothing here claims hardware acceptance.

Every check re-derives a number from the raw waveform or from the closed-form
model and compares it with what the documents say.  A check that cannot fail is
not a check, so the tolerances are stated explicitly.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

import candidates as cand
import coilmodels as cm
import datasheet_corners as dsc
import engine as e
import metrics_support as met

HERE = Path(__file__).resolve().parent
OUT = HERE / 'joint'
FAILS = []
CHECKS = []


def check(name, ok, detail=''):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILS.append('%s  %s' % (name, detail))
    print('%-58s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail))


def load(n):
    p = OUT / (n + '_metrics.json')
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    # ---- 1. the erroneous 30.44 / 52.3% basis is reproducible and is NOT used
    d = e.design(90, '1812CS-472')
    b = e.budget(d)
    mixed = 10 + b['R_coil'] + b['R_cap'] + d['branch']['R_series']
    check('old mixed-basis total reproduces 30.44 ohm', abs(mixed - 30.44) < 0.01,
          '%.4f' % mixed)
    check('mixed-basis coil share reproduces 52.3%', abs(100 * b['R_coil'] / mixed - 52.3) < 0.05,
          '%.2f%%' % (100 * b['R_coil'] / mixed))
    check('correct port-basis coil share is 53.0%',
          abs(100 * b['R_coil'] / b['Rt'] - 53.02) < 0.05, '%.2f%%' % (100 * b['R_coil'] / b['Rt']))
    check('port resistance differs from mixed basis', abs(b['Rt'] - mixed) > 0.3,
          '%.4f vs %.4f' % (b['Rt'], mixed))

    # ---- 2. three parts have three different ESRs; 15.924 is only the 472's
    esrs = {p: cm.z(p).real for p in cm.COMPARE}
    check('three parts have distinct model ESR',
          len({round(v, 3) for v in esrs.values()}) == 3,
          ' '.join('%s=%.3f' % (k[-3:], v) for k, v in esrs.items()))
    check('15.924 ohm belongs to 472 only',
          abs(esrs['1812CS-472'] - 15.9235) < 1e-3 and abs(esrs['1812CS-392'] - 15.9235) > 1,
          '392=%.3f' % esrs['1812CS-392'])
    check('Q ordering differs from ESR ordering (Q alone is not a proxy)',
          (cm.z('1812CS-392').imag / cm.z('1812CS-392').real) >
          (cm.z('1812CS-332').imag / cm.z('1812CS-332').real) and
          cm.z('1812CS-392').real > cm.z('1812CS-332').real,
          '392 Q higher, 392 ESR higher')

    # ---- 3. per-part datasheet floors are NOT one shared number
    scales = {p: dsc.loss_scale_for_q50(p) for p in cm.COMPARE}
    check('datasheet floors are solved per part, all different',
          len({round(v, 4) for v in scales.values()}) == 3,
          ' '.join('%s=%.4f' % (k[-3:], v) for k, v in scales.items()))
    for p, s in scales.items():
        q50 = cm.z(p, 50e6, s).imag / cm.z(p, 50e6, s).real
        check('floor reproduces guaranteed Q@50M for %s' % p[-3:],
              abs(q50 - dsc.QMIN50[p]) < 1e-3, 'Q50=%.4f vs %d' % (q50, dsc.QMIN50[p]))
    check('332/392 floors are worse than 472 floor (model more optimistic)',
          abs(dsc.corners('1812CS-332')['ESR31_datasheet_floor_ohm'] /
              dsc.corners('1812CS-332')['ESR31_typical_model_ohm'] - 1) >
          abs(dsc.corners('1812CS-472')['ESR31_datasheet_floor_ohm'] /
              dsc.corners('1812CS-472')['ESR31_typical_model_ohm'] - 1),
          '332 +%.1f%% vs 472 +%.1f%%' % (
              100 * (dsc.corners('1812CS-332')['ESR31_datasheet_floor_ohm'] /
                     dsc.corners('1812CS-332')['ESR31_typical_model_ohm'] - 1),
              100 * (dsc.corners('1812CS-472')['ESR31_datasheet_floor_ohm'] /
                     dsc.corners('1812CS-472')['ESR31_typical_model_ohm'] - 1)))

    # ---- 4. every transient case closes its energy budget
    worst = 0.0
    worst_name = ''
    for p in sorted(OUT.glob('*_metrics.json')):
        j = json.loads(p.read_text(encoding='utf-8'))
        rel = abs(j['energy_closure']['relative_error'])
        if rel > worst:
            worst, worst_name = rel, j['name']
    check('energy closure over ALL cases below 1e-5', worst < 1e-5,
          'worst %.2e at %s' % (worst, worst_name))

    # ---- 5. independent re-integration of one case from the raw file
    # The stored value integrates the radiator current over the samples that fall
    # inside window_s (engine.analyse keeps ta>=t0 & ta<=t1 and applies
    # metrics_support.weights).  Re-integrate that same sample interval with an
    # explicit trapezoid, so the check tests the number and not the helper.
    j = load('h90_332')
    if j:
        a = met.read_raw(OUT / 'h90_332.raw')
        t0, t1 = j.get('window_s', [None, None])
        t = a['time']
        keep = (t >= t0) & (t <= t1)
        ts, xs = t[keep], a['i(vant)'][keep]
        rms = math.sqrt(np.trapezoid(xs * xs, ts) / (ts[-1] - ts[0])) * 1e3
        check('independent trapezoid RMS matches stored I_rad_total_rms',
              abs(rms - j['I_rad_total_rms_mA']) < 1e-9,
              '%.9f vs %.9f' % (rms, j['I_rad_total_rms_mA']))
        # The window bounds are interpolated zero crossings, so they are not sample
        # times: the sample interval is a strictly smaller domain.  Integrating the
        # full continuous window must therefore agree only to the effect of the two
        # partial end intervals, which is bounded and must stay negligible.
        tw = np.r_[t0, ts[(ts > t0) & (ts < t1)], t1]
        xi = np.interp(tw, t, a['i(vant)'])
        rms_full = math.sqrt(np.trapezoid(xi * xi, tw) / (t1 - t0)) * 1e3
        check('RMS is insensitive to the window-end convention',
              abs(rms_full / j['I_rad_total_rms_mA'] - 1) < 1e-5,
              'full-window %.9f, rel %.1e' % (rms_full, rms_full / j['I_rad_total_rms_mA'] - 1))

    # ---- 6. the three principal cases exist and the ranking holds
    names = ['h90_472', 'h90_392', 'h90_332']
    js = [load(n) for n in names]
    check('all three principal 90 cm cases present', all(js), str([j is not None for j in js]))
    if all(js):
        p = [x['P_rad_mW'] for x in js]
        check('90 cm: 392 radiates more than 472', p[1] > p[0], '%.2fx' % (p[1] / p[0]))
        check('90 cm: 332 radiates more than 472', p[2] > p[0], '%.2fx' % (p[2] / p[0]))
        check('90 cm: 332 has lowest ESR and highest radiated power',
              js[2]['coil_ESR_ohm'] == min(x['coil_ESR_ohm'] for x in js) and p[2] == max(p),
              'ESR %.3f, Prad %.5f' % (js[2]['coil_ESR_ohm'], p[2]))
        # cross-check P_rad against I^2*R in the port-referred model
        for x in js:
            pi = e.port_impedance_of(dict(name=x['name'], part=x['part'],
                                          length_cm=x['length_cm']), e.design(x['length_cm'], x['part']))
            check('%s port Z real part matches stored' % x['name'],
                  abs(pi.real - x['port_R_with_10ohm']) < 1e-6,
                  '%.6f' % pi.real)
            check('%s port Z is resonant at 31 MHz' % x['name'],
                  abs(pi.imag) < 1e-6, 'Im=%.2e' % pi.imag)

    # ---- 7. the 100 cm check is independent and agrees
    j100 = load('h100_332')
    j90 = load('h90_332')
    if j100 and j90:
        r100 = load('h100_392')['P_rad_mW'] / load('h100_472')['P_rad_mW']
        r90 = load('h90_392')['P_rad_mW'] / load('h90_472')['P_rad_mW']
        check('392/472 advantage agrees at 90 and 100 cm within 5%',
              abs(r100 / r90 - 1) < 0.05, '%.3f vs %.3f' % (r90, r100))

    # ---- 8. every corner keeps the ordering
    corner_suffix = ['_Lm5', '_Lp5', '_loss2', '_Qds', '_srf', '_ct2', '_cb2', '_cx5']
    bad = []
    for suf in corner_suffix:
        a = load('h90_472' + suf)
        bb = load('h90_392' + suf)
        cc = load('h90_332' + suf)
        if not (a and bb and cc):
            bad.append(suf + '(missing)')
            continue
        if not (bb['P_rad_mW'] > a['P_rad_mW'] and cc['P_rad_mW'] > a['P_rad_mW']):
            bad.append(suf)
    check('ordering survives every corner', not bad, ','.join(bad) or 'all %d corners' % len(corner_suffix))

    # ---- 9. trimmer alone is only possible for 472
    rows = json.loads((HERE / 'analytic_sweep.json').read_text(encoding='utf-8'))
    trim = {r['part']: r['trim_only'] for r in rows if r['length_cm'] == 90 and r['buildable']}
    check('90 cm: only 472 fits the 2-18 pF trimmer alone',
          trim.get('1812CS-472') is True and trim.get('1812CS-392') is False
          and trim.get('1812CS-332') is False, str(trim))

    # ---- 10. no case claims hardware acceptance
    check('no case claims measured antenna parameters',
          all(json.loads(p.read_text(encoding='utf-8')).get('design_only', False) or
              'typical' in json.loads(p.read_text(encoding='utf-8')).get('caveat', '').lower()
              for p in OUT.glob('*_metrics.json')),
          'caveat present in every metrics file')

    # ---- 11. ideal-coil ceiling is bounded and less than the coil saving suggests
    b472 = e.budget(e.design(90, '1812CS-472'))
    b472i = e.budget(e.design(90, '1812CS-472', coil_loss_scale=1e-6))
    gain = b472i['eta'] / b472['eta']
    check('ideal-coil ceiling is finite and below 2.2x', 1.5 < gain < 2.2, '%.2fx' % gain)

    # Completeness and cache provenance must be checked before claiming success.
    from reanalyse import job_from_metrics
    expected = cand.make(cand.BASE_CASES + cand.SECONDARY_CASES + cand.CORNER_CASES)
    expected_names = {j['name'] for j in expected}
    expected_names.update('h90_' + p + '_Qx' for p in ('332', '392', '472'))
    check('all 33 raw/cir/metrics triplets present', all(
        (OUT / (n + ext)).exists() for n in expected_names
        for ext in ('.raw', '.cir', '_metrics.json')), str(len(expected_names)))
    for name, target in {'h90_332': 0.018021, 'h90_392': 0.016711,
                         'h90_472': 0.013272, 'h100_332': 0.021725,
                         'h100_472': 0.015895}.items():
        item = load(name)
        check(name + ' restored nominal radiation agrees with handoff',
              item is not None and abs(item['P_rad_mW'] - target) < 5e-7,
              'target %.6f mW' % target)
    for job in expected:
        j = load(job['name'])
        if not j:
            check(job['name'] + ' metrics present', False)
            continue
        stored_job = job_from_metrics(j)
        txt, d = e.netlist(job)
        cir = OUT / (job['name'] + '.cir')
        check(job['name'] + ' canonical netlist', cir.exists() and
              e._electrical(cir.read_text(encoding='utf-8')) == e._electrical(txt))
        check(job['name'] + ' assumptions match requested corner',
              all(math.isclose(stored_job.get(k, True if k == 'retune' else float('nan')), v, rel_tol=1e-12, abs_tol=1e-30)
                  for k, v in job.items() if k not in ('name', 'part', 'length_cm')))
        if job['name'].endswith(('_Lm5', '_Lp5', '_cx5')):
            base = load(job['name'].rsplit('_', 1)[0])
            check(job['name'] + ' detunes and reduces radiation',
                  not j['assumptions']['retune'] and abs(j['port_Z31'][1]) > 1
                  and base is not None and j['P_rad_mW'] < base['P_rad_mW'])
        actual = e.netlist_port_impedance(job, d)
        check(job['name'] + ' actual netlist port impedance recorded',
              abs(complex(*j.get('netlist_port_Z31', [0, 0])) - actual) < 1e-8)

    # ---- 12. the documented netlist-vs-analytic ESR gap is recomputable
    # 05 section 8 quotes the frozen-netlist coil ESR next to the analytic one.
    # That is a claim about the model, so re-derive it instead of trusting prose.
    net_esr = {}
    for tag in ('332', '392', '472'):
        p = cm.PARTS['1812CS-' + tag]
        series = (p['R2'] + p['k'] * math.sqrt(e.F0)) + 1j * e.W0 * p['L_uH'] * 1e-6
        parallel = p['R1'] + 1 / (1j * e.W0 * p['Cp_pF'] * 1e-12)
        net_esr[tag] = (1 / (1 / series + 1 / parallel)).real
    doc05 = (HERE / '05_瞬态验证与边界.md').read_text(encoding='utf-8')
    quoted = all(('%.3f' % v) in doc05 for v in net_esr.values())
    check('netlist coil ESR quoted in 05 S8 equals recomputation',
          quoted and all(net_esr[t] > cm.z('1812CS-' + t).real for t in net_esr),
          ' '.join('%s=%.3f(analytic %.3f)' % (t, net_esr[t], cm.z('1812CS-' + t).real)
                   for t in ('332', '392', '472')))

    # ---- 13. every table pasted into a document still equals its rendered copy
    # The stage rule is "no number in the markdown is typed by hand".  Hand edits
    # had already drifted by one unit in the last digit, so the documents are
    # compared against the rendered tables rather than trusted.
    tables = {p.name: p.read_text(encoding='utf-8').strip()
              for p in HERE.glob('table_*.md')}
    docs = ['04_候选对照与验证.md', 'README.md']
    drift = []
    for doc in docs:
        text = (HERE / doc).read_text(encoding='utf-8')
        for name, body in tables.items():
            head = body.splitlines()[0]
            if head not in text:
                continue
            # the document must contain the rendered table verbatim, not a variant
            if body not in text:
                drift.append('%s <- %s' % (doc, name))
    check('pasted tables are verbatim copies of the rendered tables', not drift,
          ', '.join(drift) or '%d tables in %d docs' % (len(tables), len(docs)))

    # ---- write results
    out = dict(status='PASS' if not FAILS else 'FAIL', checks=len(CHECKS),
               failures=FAILS, case_count=len(list(OUT.glob('*_metrics.json'))),
               worst_energy_closure=worst, worst_energy_closure_case=worst_name,
               model_limitations=['Analytic coil topology and frozen transient topology differ; see 05 section 8',
                                  'Q31 floor is model-derived, not a vendor guarantee'],
               hardware_acceptance=False,
               note='Checks re-derive numbers from raw waveforms and from the closed-form '
                    'model. PASS validates the listed numerical/cache checks, NOT that the '
                    'hardware works.')
    (HERE / 'verification.json').write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                            encoding='utf-8')
    print()
    print('%d checks, %d failures' % (len(CHECKS), len(FAILS)))
    if FAILS:
        for f in FAILS:
            print('  FAILED:', f)
        sys.exit(1)
    print('PASS')


if __name__ == '__main__':
    main()
