"""AM-ALT.3.4 engine: rigorous port-referred power accounting on ONE current basis.

Design rules enforced here (they are the reason this stage exists):

1.  Every power term is obtained from the SAME waveforms of the SAME case, with
    a 0 V current-sense source in every branch.  Nothing is referred across
    current bases by hand, so the terms close against the driver power by
    construction and the check is asserted, not assumed.

2.  The radiator branch contains BOTH radiation and ohmic loss:
        R_ant_series(31 MHz) = R_radiated + R_wire + R_ground   (NEC split)
    plus the contact resistance in series.  The table therefore separates
    "radiated" from "antenna ohmic", never merging them into one number.

3.  Coil ESR comes from the manufacturer TYPICAL lumped model (Document 158).
    It is labelled as such everywhere; it is never called measured or
    guaranteed, and it is NEVER split into skin / proximity / core percentages
    because Document 158's elements are fitted as a whole ("individual elements
    of the model are not determined by parameter measurement").

4.  Q = X/R at 31 MHz is a SCREENING number, not the objective.  The objective
    is radiated power at the frozen driver after each candidate is retuned to
    resonance on its own, including the loss of whatever compensation element
    that retuning requires.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'stage_am_alt3_3_20261117'
sys.path.insert(0, str(PREV))
import metrics_support as met            # noqa: E402
import coilmodels as cm                  # noqa: E402

BASE = PREV.parent / 'stage_am_alt3_20261115/round2_20261116/netlists/d05.cir'
NG = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
OUT = HERE / 'joint'
OUT.mkdir(exist_ok=True)

F0 = 31e6
W0 = 2 * math.pi * F0
ETA0 = 376.730313668
RSENSE = 10.0            # FIXED reference shunt for every candidate comparison
LEAD_H = 2e-9            # series lead inductance (initial model assumption)
CONTACT = 0.2            # contact resistance (initial model assumption)
CBASE = 0.5e-12          # feed-to-RF-ground capacitance (initial model assumption)
TRIM_TAND = 0.0025       # Vishay BFC280905217 tan-delta at 100 MHz, applied at 31 MHz
COG_TAND = 1.0e-4        # class-1 C0G assumption, sensitivity-checked

ANTS = {round(a['length_m'] * 100): a
        for a in json.loads((PREV / 'antenna_nominal.json').read_text(encoding='utf-8'))}


def antenna_branch(length_cm, contact=CONTACT, cant_scale=1.0):
    a = ANTS[length_cm]
    R_series = a['R'] + contact
    L = a['Lant_H']
    C = a['Cant_F'] * cant_scale
    return dict(z_series=R_series + 1j * (W0 * L - 1 / (W0 * C)),
                R_series=R_series, Lant=L, Cant=C, contact=contact,
                R_radiated=a['R_radiated'], R_wire=a['R_wire'],
                R_ground=a['R_ground'],
                R_ohmic=a['R'] - a['R_radiated'] + contact, raw=a)


TRIM_MIN, TRIM_MAX = 2e-12, 18e-12   # Vishay BFC280905217 range


def cap_esr(C, tand=TRIM_TAND):
    if C <= 0:
        return 0.0
    return tand / (W0 * C)


def cap_network(C_total, trim_tand=TRIM_TAND, cog_tand=COG_TAND):
    """Split the required series capacitance into trimmer || C0G.

    The previous round charged the WHOLE capacitance at the trimmer's
    tan-delta, which is pessimistic for the C0G part but also hid the fact
    that 332/392 cannot be built from the trimmer alone: they need a fixed
    C0G in parallel, and that extra part brings its own loss and parasitics.
    Here the split is explicit and both branches are modelled.

    Returns the trimmer setting, the C0G value and the series-equivalent
    resistance of the parallel pair (exact complex parallel at 31 MHz).
    """
    if C_total <= 0:
        raise ValueError('non-positive capacitance')
    if C_total <= TRIM_MAX:
        C_t, C_c = C_total, 0.0
    else:
        C_t, C_c = TRIM_MAX, C_total - TRIM_MAX
    z_t = (cap_esr(C_t, trim_tand) + 1 / (1j * W0 * C_t)) if C_t > 0 else None
    z_c = (cap_esr(C_c, cog_tand) + 1 / (1j * W0 * C_c)) if C_c > 0 else None
    if z_c is None:
        z_par = z_t
    elif z_t is None:
        z_par = z_c
    else:
        z_par = z_t * z_c / (z_t + z_c)
    return dict(C_total=C_total, C_trim=C_t, C_cog=C_c,
                r_trim=cap_esr(C_t, trim_tand) if C_t > 0 else 0.0,
                r_cog=cap_esr(C_c, cog_tand) if C_c > 0 else 0.0,
                r_series=z_par.real, z=z_par,
                trim_only=bool(C_total <= TRIM_MAX),
                extra_C0G_pF=max(0.0, (C_total - TRIM_MAX) * 1e12))


def design(length_cm, part, contact=CONTACT, cbase=CBASE, cant_scale=1.0,
           coil_loss_scale=1.0, coil_extra_C_pF=0.0, trim_tand=TRIM_TAND,
           retune=True, coil_L_scale=1.0):
    """Total series C that resonates this candidate at 31 MHz (trimmer || C0G).

    retune=False keeps the capacitance the part needs WITHOUT the added parasitic,
    so the extra capacitance actually detunes the network.  With retune=True the
    added C is simply absorbed into the (recomputed) tuning capacitance and the
    "extra 0.5 pF" corner becomes meaningless: it produced a 0.0 % change on the
    472, which is what exposed the problem.
    """
    # Two stages of tolerance are modelled separately:
    #   * the part as purchased   -> zc_nominal (nominal L, NO stray, nominal loss)
    #   * the part as installed   -> zc_actual  (L tolerance + stray + loss corner)
    zc_nominal = cm.z(part, F0, coil_loss_scale, 0.0)
    zc = cm.z(part, F0, coil_loss_scale, coil_extra_C_pF * 1e12)  # helper takes pF
    if coil_L_scale != 1.0:
        zc = zc.real + 1j * (zc.imag * coil_L_scale)
    br = antenna_branch(length_cm, contact, cant_scale)
    zb = br['z_series']
    zb_c = 1.0 / (1.0 / zb + 1j * W0 * cbase)

    # The tuning capacitance is always solved on the NOMINAL part: a trimmer is
    # set at 31 MHz and then the tolerances happen.  When retune is True the
    # corner asks "what if we re-trim after the tolerance", so the scaled values
    # are folded in before solving; when retune is False the nominal solution is
    # kept and the tolerances detune the network.
    # Solve the trimmer on the nominal part when the corner is a stress, and on the
    # actual part when the corner says "we re-trim after the tolerance".
    zc_for_tuning = zc if retune else zc_nominal
    x_total = (zc_for_tuning + zb_c).imag + W0 * LEAD_H
    if x_total <= 0:
        raise ValueError('%s at %d cm needs a series INDUCTOR, not a capacitor'
                         % (part, length_cm))
    C = 1.0 / (W0 * x_total)
    # CINSTALL shunts the coil only; cm.z already includes it.
    net = cap_network(C, trim_tand)
    return dict(part=part, length_cm=length_cm, C_total_pF=C * 1e12,
                coil_z=zc, branch=br, z_branch_with_cbase=zb_c,
                z_branch_eff=zb_c,      # antenna branch; CINSTALL is included in coil_z
                x_total=x_total, cap=net, cap_r=net['r_series'],
                trim_tand=trim_tand)


def budget(design_, rsense=RSENSE):
    """Analytic port-referred budget (series equivalent, 31 MHz, no transient)."""
    d = design_
    br = d['branch']
    zb = br['z_series']
    # branch current relative to port current, with CBASE shunting
    i_ratio = abs(1.0 / (1.0 + 1j * W0 * (CBASE) * zb))       # |I_branch/I_port|
    k2 = 1.0 / i_ratio ** 2
    R_ant_port = br['R_series'] / k2
    R_rad_port = br['R_radiated'] / k2
    R_ohmic_port = (br['R_series'] - br['R_radiated']) / k2
    Rt = rsense + d['coil_z'].real + d['cap_r'] + R_ant_port
    return dict(k2=k2, R_coil=d['coil_z'].real, R_cap=d['cap_r'],
                R_ant_port=R_ant_port, R_rad_port=R_rad_port,
                R_ohmic_port=R_ohmic_port, R_sense=rsense, Rt=Rt,
                eta=R_rad_port / Rt)


# --------------------------------------------------------------------------
# netlist with a 0 V sense source in every branch
# --------------------------------------------------------------------------
def _load_block(job):
    part = job['part']
    d = design(job['length_cm'], part,
               contact=job.get('contact', CONTACT),
               cbase=job.get('cbase', CBASE),
               cant_scale=job.get('cant_scale', 1.0),
               coil_loss_scale=job.get('coil_loss_scale', 1.0),
               coil_extra_C_pF=job.get('coil_extra_C_pF', 0.0),
               trim_tand=job.get('trim_tand', TRIM_TAND),
               retune=job.get('retune', True),
               coil_L_scale=job.get('coil_L_scale', 1.0))
    p = cm.PARTS[part]
    net = d['cap']
    C = net['C_trim']
    r_trim = net['r_trim']
    C_cog = net['C_cog']
    r_cog = net['r_cog']
    ls = job.get('coil_loss_scale', 1.0)
    r2 = p['R2'] * ls
    rskin = p['k'] * math.sqrt(F0) * ls
    l = p['L_uH'] * 1e-6 * job.get('coil_L_scale', 1.0)
    cp = p['Cp_pF'] * 1e-12
    r1 = p['R1'] * ls
    # The job dict carries SI units everywhere (see reanalyse.KEYMAP, which does the
    # pF -> F conversion once).  Multiplying by 1e-12 again here turned a 0.5 pF
    # stray into 5e-25 F, i.e. no stray at all, which is why every _cx5 corner
    # kept reproducing the nominal result.
    extra = job.get('coil_extra_C_pF', 0.0)
    base = job.get('cbase', CBASE)
    br = antenna_branch(job['length_cm'], job.get('contact', CONTACT),
                        job.get('cant_scale', 1.0))
    return d, f"""* AM-ALT.3.4 candidate {job['name']}
* Coilcraft {part}: Document 158 TYPICAL lumped model, Rskin frozen at 31 MHz.
* Retuned to 31 MHz for THIS candidate; trimmer loss included.
VRS  sense_out rs_node 0
VCOIL rs_node coil_a 0
RCOILDC coil_a coil_b {r2:.12g}
RCOILSKIN coil_b coil_c {rskin:.12g}
LTUNE coil_c coil_out {l:.12g}
CCOIL coil_a coil_d {cp:.12g}
RCOILPAR coil_d coil_out {r1:.12g}
CINSTALL rs_node coil_out {max(extra,1e-18):.12g}
CTRIM coil_out trim_a {C:.12g}
RTRIM trim_a trim_b {r_trim:.12g}
{'' if C_cog <= 0 else 'CCOG coil_out cog_a %.12g' % C_cog}
{'' if C_cog <= 0 else 'RCOG cog_a trim_b %.12g' % r_cog}
LLEAD trim_b ant_feed {LEAD_H:.12g}
CBASE ant_feed cb_ret {base:.12g}
VCB cb_ret 0 0
VANT ant_feed ant_r 0
RANT ant_r ant_l {br['R_series']:.12g}
LANT ant_l ant_n2 {br['Lant']:.12g}
CANT ant_n2 0 {br['Cant']:.12g}
"""


def netlist(job):
    d, load = _load_block(job)
    t = BASE.read_text(encoding='utf-8')
    t = re.sub(r'^LTUNE .*?^CANT .*?$', load.rstrip(), t, flags=re.M | re.S)
    t = t.replace('RSENSE ef_e sense_out 10', 'RSENSE ef_e sense_out %.12g' % job.get('rsense', RSENSE))
    t = t.replace('i(ltune) i(vsup)',
                  'i(ltune) i(vant) i(vrs) i(vcoil) i(vcb) i(llead) '
                  'v(ant_feed) v(ant_r) v(ant_l) v(ant_n2) v(sense_out) v(rs_node) '
                  'v(coil_out) v(coil_a) v(trim_b) i(vsup)')
    step = job.get('step_ns', .25)
    t = re.sub(r'^tran .*$', 'tran %gn 0.002 0.00185 %gn uic' % (step, step), t, flags=re.M)
    t = t.replace('write d05.raw', "write %s.raw" % job['name'])
    return t, d


def _electrical(txt):
    """Netlist text with the 'save' line normalised to a set.

    The save list is a probe request, not part of the circuit.  Reordering the
    same probes must NOT invalidate a cached .raw: doing so silently re-ran
    dozens of 10-minute simulations for no physical change.
    """
    out = []
    for ln in txt.splitlines():
        if ln.startswith('save '):
            toks = sorted(set(ln.split()[1:]))
            out.append('save ' + ' '.join(toks))
        else:
            out.append(ln)
    return '\n'.join(out)


def run(job, force=False):
    name = job['name']
    path = OUT / (name + '.cir')
    raw = OUT / (name + '.raw')
    txt, d = netlist(job)
    if raw.exists() and not force:
        old = path.read_text(encoding='utf-8') if path.exists() else ''
        if old and _electrical(old) != _electrical(txt):
            raw.unlink()          # genuinely different circuit
    path.write_text(txt, encoding='utf-8')
    if force and raw.exists():
        raw.unlink()
    if not raw.exists():
        with (OUT / (name + '.log')).open('w') as log:
            z = subprocess.run([str(NG), '-b', path.name], cwd=OUT, stdout=log,
                               stderr=subprocess.STDOUT, timeout=7200)
        if z.returncode:
            raise RuntimeError('ngspice failed: ' + name)
    return analyse(job, d)


# --------------------------------------------------------------------------
# metrics: everything from one set of waveforms
# --------------------------------------------------------------------------
def _fund(t, x, w, f):
    ph = 2 * np.pi * f * (t - t[0])
    A = np.column_stack((np.sin(ph), np.cos(ph)))
    coef = np.linalg.solve(A.T @ (w[:, None] * A), A.T @ (w * x))
    return float(np.hypot(*coef) / np.sqrt(2))


def analyse(job, d):
    name = job['name']
    a = met.read_raw(OUT / (name + '.raw'))
    # metrics_support.analyse fits its carrier and plateau numbers on the variable
    # named i(ltune).  This stage has a real i(ltune) (the coil branch), so the
    # same substitution the previous round used is applied explicitly: the
    # metrics are computed on the RADIATOR current i(vant), which is the current
    # that produces radiation.
    _orig = met.read_raw

    def _on_radiator(p):
        dd = _orig(p)
        dd['i(ltune)'] = dd['i(vant)']
        return dd

    met.read_raw = _on_radiator
    try:
        m = met.analyse(OUT / (name + '.raw'))
    finally:
        met.read_raw = _orig
    t0, t1 = m['window_s']
    ta = a['time']
    keep = (ta >= t0) & (ta <= t1)
    a = {k: v[keep] for k, v in a.items()}
    t = a['time']
    w = met.weights(t)
    w = w / w.sum()
    f = m['carrier_Hz']

    i_port = a['i(vrs)']
    i_coil = a['i(vcoil)']
    i_cap = a['i(llead)']
    i_rad = a['i(vant)']
    i_cb = a['i(vcb)']

    v_rs = a['v(ef_e)'] - a['v(sense_out)']
    v_coil = a['v(rs_node)'] - a['v(coil_out)']
    v_cap = a['v(coil_out)'] - a['v(trim_b)']
    v_ant = a['v(ant_r)']          # VANT is 0 V; the branch sits between ant_r and 0
    v_cb = a['v(ant_feed)']

    def pm(v, i):
        return float(w @ (v * i))

    P_sense = pm(v_rs, i_port)
    P_coil = pm(v_coil, i_coil)
    P_cap = pm(v_cap, i_cap)
    P_ant = pm(v_ant, i_rad)
    P_cb = pm(v_cb, i_cb)
    # CINSTALL hangs from rs_node to coil_out, so it is NOT inside i(vcoil).
    # Its current follows from KCL at rs_node without needing another probe:
    #   i(vrs) in = i(vcoil) out + i(CINSTALL) out
    # Omitting this term is exactly what made the 0.5 pF corner close only to 2e-5.
    i_cbpass = i_port - i_coil
    P_cbpass = pm(a['v(rs_node)'] - a['v(coil_out)'], i_cbpass)
    P_driver = pm(a['v(ef_e)'], i_port)
    P_into_network = pm(a['v(sense_out)'], i_port)

    br = d['branch']
    frac_rad = br['R_radiated'] / br['R_series']
    P_rad = P_ant * frac_rad
    P_ant_ohmic = P_ant * (1 - frac_rad)

    closure = P_sense + P_coil + P_cap + P_ant + P_cb + P_cbpass
    rel = (closure - P_driver) / P_driver

    # fundamental currents for the report
    ir = _fund(t, i_rad, w, f)
    ip = _fund(t, i_port, w, f)

    eta_match = P_rad / P_into_network if P_into_network else float('nan')
    eta_driver = P_rad / P_driver if P_driver else float('nan')
    batt = m['battery_budget_mW']
    eta_batt = P_rad * 1e3 / batt if batt else float('nan')

    ang = ANTS[job['length_cm']]
    gains = [p[4] for p in ang['pattern'] if p[0] == 65.0]
    g = 10 ** (float(np.mean(gains)) / 10)
    e_per_a = math.sqrt(ETA0 * ang['R'] * g / (2 * math.pi * 6 ** 2))
    voc_need = 4 / (.4777 * (m['modulation_index'] / .5)) * 1e-3
    req_ma = voc_need / e_per_a * 1000
    # E_peak = I_rms * (E_peak per I_rms)  [V/m];  the RX conversion coefficient
    # 0.4777 Vpp per mV/m is the previous round's hypothesis, carried unchanged so
    # the numbers stay comparable.  It is a hypothesis, not a measurement.
    v2 = ir * e_per_a * 1000 * .4777 * (m['modulation_index'] / .5)

    pi = port_impedance_of(job, d)   # d already carries the detuned branch when retune=False

    # Device stress: same definition as the previous round (VCE*IC + VBE*IB),
    # recomputed here because metrics_support does not return it.
    def _dev(q, vc, ve, vb):
        ic = a['i(@' + q + '[ic])']
        ib = a['i(@' + q + '[ib])']
        p = (a[vc] - a[ve]) * ic + (a[vb] - a[ve]) * ib
        return dict(peak_ic_A=float(max(ic)), avg_power_W=float(w @ p),
                    peak_power_W=float(max(p)))

    qce = _dev('qce', 'v(drv_c)', 'v(drv_e)', 'v(drv_b)')
    qef = _dev('qef', 'v(vcc)', 'v(ef_e)', 'v(drv_c)')

    # Envelope edge metrics, same definition as the previous round
    # (per-RF-cycle peaks against the two plateau medians).
    cross = np.flatnonzero((i_rad[:-1] < 0) & (i_rad[1:] >= 0))
    pk = np.array([max(abs(i_rad[l:r + 1])) for l, r in zip(cross[:-1], cross[1:])]) * 1e3
    hp = m['high_plateau_median_peak_mA']
    lp = m['low_plateau_median_peak_mA']
    overshoot = float((max(pk) - hp) / (hp - lp) * 100)
    undershoot = float((lp - min(pk)) / (hp - lp) * 100)

    out = dict(
        name=name, part=job['part'], length_cm=job['length_cm'], rsense_ohm=job.get('rsense', RSENSE),
        carrier_Hz=f, modulation_index=m['modulation_index'],
        I_rad_carrier_mA=ir * 1e3, I_port_carrier_mA=ip * 1e3,
        I_rad_total_rms_mA=float(np.sqrt(w @ (i_rad ** 2)) * 1e3),
        C_total_pF=d['C_total_pF'],
        coil_ESR_ohm=d['coil_z'].real, coil_X31_ohm=d['coil_z'].imag,
        coil_Q31=d['coil_z'].imag / d['coil_z'].real,
        port_Z31=[pi.real, pi.imag],
        netlist_port_Z31=[netlist_port_impedance(job, d).real, netlist_port_impedance(job, d).imag], port_R_with_10ohm=pi.real,
        P_rad_mW=P_rad * 1e3, P_driver_mW=P_driver * 1e3,
        P_into_matching_mW=P_into_network * 1e3,
        P_sense_mW=P_sense * 1e3, P_coil_mW=P_coil * 1e3,
        P_cap_mW=P_cap * 1e3, P_ant_ohmic_mW=P_ant_ohmic * 1e3,
        P_cbase_mW=P_cb * 1e3, P_coil_bypass_mW=P_cbpass * 1e3, P_ant_total_mW=P_ant * 1e3,
        eta_match_to_rad_pct=100 * eta_match,
        eta_driver_to_rad_pct=100 * eta_driver,
        eta_battery_to_rad_pct=100 * eta_batt,
        battery_mW=batt,
        V2_est_Vpp=v2, required_carrier_mA=req_ma,
        link_shortfall=req_ma / (ir * 1e3),
        min_QCE_VCE_V=m['minimum_QCE_VCE_V'], min_QEF_VCE_V=m['minimum_QEF_VCE_V'],
        qce_peak_ic_mA=qce['peak_ic_A'] * 1e3, qef_peak_ic_mA=qef['peak_ic_A'] * 1e3,
        qce_avg_power_mW=qce['avg_power_W'] * 1e3, qce_peak_power_mW=qce['peak_power_W'] * 1e3,
        qef_avg_power_mW=qef['avg_power_W'] * 1e3, qef_peak_power_mW=qef['peak_power_W'] * 1e3,
        overshoot_pct=overshoot, undershoot_pct=undershoot,
        antenna_peak_V=float(max(abs(a['v(ant_feed)']))),
        step_ns=job.get('step_ns', .25),
        window_s=[float(t0), float(t1)],
        assumptions=dict(contact_ohm=job.get('contact', CONTACT),
                         cbase_pF=job.get('cbase', CBASE) * 1e12,
                         cant_scale=job.get('cant_scale', 1.0),
                         coil_loss_scale=job.get('coil_loss_scale', 1.0),
                         coil_L_scale=job.get('coil_L_scale', 1.0),
                         coil_extra_C_pF=job.get('coil_extra_C_pF', 0.0) * 1e12,
                         retune=job.get('retune', True),
                         trim_tand=job.get('trim_tand', TRIM_TAND)),
        energy_closure=dict(sum_of_measured_parts_mW=closure * 1e3,
                            driver_out_mW=P_driver * 1e3,
                            relative_error=rel,
                            note='closure = RSENSE + coil + CINSTALL bypass + trimmer + '
                                 'antenna branch + CBASE, all from the same waveforms'),
        caveat='Manufacturer TYPICAL lumped model, not a guarantee and not a measurement. '
               'Skin resistance frozen at 31 MHz. No per-mechanism ESR split is claimed. '
               'RX transfer coefficient 1 m is a hypothesis, not a measurement.',
    )
    (OUT / (name + '_metrics.json')).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out


def port_impedance_of(job, d):
    """Series port impedance seen by the frozen driver (includes RSENSE).

    Analytic tuning-model impedance. CINSTALL occurs in coil_z exactly once.
    netlist_port_impedance separately reports the frozen netlist topology.
    """
    zb_c = d['z_branch_eff']
    C = d['C_total_pF'] * 1e-12
    return (job.get('rsense', RSENSE) + d['coil_z'] + d['cap_r']
            + 1j * W0 * LEAD_H + zb_c - 1j / (W0 * C))


def line(o):
    return ('%-24s %-12s %3d  Irad %7.4f mA  V2 %5.3f  Prad %8.5f mW  '
            'eta_m %6.3f%%  eta_b %6.3f%%  Rt %6.3f  C %7.3f pF' %
            (o['name'], o['part'], o['length_cm'], o['I_rad_carrier_mA'],
             o['V2_est_Vpp'], o['P_rad_mW'], o['eta_match_to_rad_pct'],
             o['eta_battery_to_rad_pct'], o['port_R_with_10ohm'], o['C_total_pF']))


def netlist_port_impedance(job, d):
    """Independent AC reduction of the actual frozen transient load topology.

    The historical analytic model places R2 outside the parallel branch;
    the frozen netlist places it inside. Keep both explicitly, never claim
    their ESR values are identical. This function does not change tuning.
    """
    p = cm.PARTS[job['part']]
    scale = job.get('coil_loss_scale', 1.0)
    series = (p['R2'] + p['k'] * math.sqrt(F0)) * scale + 1j * W0 * p['L_uH'] * 1e-6 * job.get('coil_L_scale', 1.0)
    parallel = p['R1'] * scale + 1 / (1j * W0 * p['Cp_pF'] * 1e-12)
    coil = 1 / (1 / series + 1 / parallel + 1j * W0 * max(job.get('coil_extra_C_pF', 0), 1e-18))
    br = d['branch']['z_series']
    antenna = 1 / (1 / br + 1j * W0 * job.get('cbase', CBASE))
    return job.get('rsense', RSENSE) + coil + d['cap']['z'] + 1j * W0 * LEAD_H + antenna
