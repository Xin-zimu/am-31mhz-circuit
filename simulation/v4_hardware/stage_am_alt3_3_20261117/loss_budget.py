"""Where does the RF power go? Port-referred loss budget at 31 MHz.

Every resistance below is referred to the SAME current (the port current), so the
terms are directly comparable and their sum equals the port series resistance used
by joint_sim.

The antenna branch (R + contact + jX) sits in parallel with the base capacitance, so
only part of the port current reaches it. Referring to the port current divides the
branch resistance by k^2, where k^2 = |1 + jw*Cbase*Zbranch|^2.
"""
import json, math
from pathlib import Path
import joint_sim as s

W = s.W
ROOT = Path(__file__).resolve().parent
ants = json.loads((ROOT / 'antenna_nominal.json').read_text(encoding='utf-8'))


def budget(d, rsense=10.0, contact=.2, base=.5e-12, cscale=1.0):
    za = s.ant(d, contact=contact, base=base, cscale=cscale)   # branch || Cbase
    z = s.coil()
    c = 1 / (W * ((z + za).imag + W * 2e-9))
    capr = .0025 / (W * c)

    zbranch = (d['R'] + contact) + 1j * (W * d['Lant_H'] - 1 / (W * d['Cant_F'] * cscale))
    k2 = abs(1 + 1j * W * base * zbranch) ** 2      # = |I_port|^2 / |I_branch|^2

    r_branch_port = (d['R'] + contact) / k2
    r_rad_port = d['R_radiated'] / k2
    r_antloss_port = r_branch_port - r_rad_port

    # Radiation is part of the port resistance, not an extra term: the port I^2R budget
    # splits into (loss terms) + (radiated term), and together they equal Rt.
    parts = dict(RSENSE=rsense, COIL=z.real, ANTENNA_LOSS=r_antloss_port, TRIM_CAP=capr)
    rt = sum(parts.values()) + r_rad_port
    rt_direct = rsense + z.real + za.real + capr        # cross-check against joint_sim
    return dict(parts=parts, Rt=rt, Rt_direct=rt_direct, k2=k2,
                R_rad_port=r_rad_port,
                eta_driver=r_rad_port / rt,
                eta_antenna=r_rad_port / (rt - rsense),
                C_req_pF=c * 1e12)


def main():
    # Baseline of record: 90 cm radiator, 1812CS-472, 10 ohm shunt, frozen driver.
    # Every share printed below belongs to THIS part. Other coils have different ESR
    # (392: 11.50 ohm, 332: 10.25 ohm) and therefore different shares - do not reuse.
    d90 = next(x for x in ants if x['length_m'] == .9)
    b = budget(d90)
    print('=== 90 cm nominal, RSENSE = 10 ohm ===')
    print('Ctotal = %.3f pF' % b['C_req_pF'])
    print('k^2 (port/branch current ratio) = %.4f  -> branch current is %.1f%% of port'
          % (b['k2'], 100 / b['k2'] ** .5))
    print('Rt from parts = %.4f ohm ; Rt direct from joint_sim macro = %.4f ohm'
          % (b['Rt'], b['Rt_direct']))
    assert abs(b['Rt'] - b['Rt_direct']) < 1e-9, 'budget does not close'
    print()
    print('%-16s %12s %10s' % ('element', 'ohm (port-ref)', 'share'))
    for k, v in b['parts'].items():
        print('%-16s %12.3f %9.1f%%' % (k, v, 100 * v / b['Rt']))
    print('%-16s %12.3f %9.1f%%' % ('RADIATED', b['R_rad_port'], 100 * b['R_rad_port'] / b['Rt']))
    print('%-16s %12.3f %9.1f%%' % ('= RTOTAL', b['Rt'], 100.0))
    print()
    print('eta vs driver output (incl. shunt): %.2f%%' % (100 * b['eta_driver']))
    print('eta vs antenna port (shunt excluded): %.2f%%' % (100 * b['eta_antenna']))
    print()

    # --- power must use a consistent current basis ---
    # I(VANT) is the BRANCH current; the shunt sees the PORT current. Mixing them
    # double-counts (or omits) the k^2 base-capacitance divider.
    metrics = json.loads((ROOT / 'joint' / 'h90_nom_metrics.json').read_text(encoding='utf-8'))
    Ib = metrics['carrier_fundamental_rms_mA'] * 1e-3      # branch, carrier
    Ip = Ib * math.sqrt(b['k2'])                            # port, carrier
    Rb = b['R_rad_port'] * b['k2']                          # branch-referred radiation resistance
    print('=== carrier-frequency power, 90 cm ===')
    print('I_branch (I(VANT))      = %.4f mA' % (Ib * 1e3))
    print('I_port   = Ib*sqrt(k2)  = %.4f mA' % (Ip * 1e3))
    print('R_rad branch-referred   = %.6f ohm' % Rb)
    print('R_rad port-referred     = %.6f ohm' % b['R_rad_port'])
    print()
    p_rad_b = Ib ** 2 * Rb * 1e3
    p_rad_p = Ip ** 2 * b['R_rad_port'] * 1e3
    p_sense = Ip ** 2 * 10 * 1e3
    print('P_rad = Ib^2*Rrad_branch = %.6f mW' % p_rad_b)
    print('P_rad = Ip^2*Rrad_port   = %.6f mW   <- must agree' % p_rad_p)
    assert abs(p_rad_b - p_rad_p) < 1e-12
    print('P_sense = Ip^2*10        = %.6f mW' % p_sense)
    print('ratio sense/radiated     = %.2f x' % (p_sense / p_rad_b))
    print()
    print('NOTE: this table is carrier-only. The modulated total RMS is a different')
    print('quantity and is reported separately in 04 (total_time_weighted_rms_mA).')
    print()

    print('=== shunt sweep (90 cm) ===')
    print('%8s %9s %12s %13s' % ('RSENSE', 'Rt', 'eta_driver%', 'eta_ant%'))
    rows = []
    for rs in [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.01]:
        bb = budget(d90, rsense=rs)
        print('%8.2f %9.3f %12.2f %13.2f' % (rs, bb['Rt'], 100 * bb['eta_driver'], 100 * bb['eta_antenna']))
        rows.append(dict(rsense=rs, Rt=bb['Rt'], eta_driver=bb['eta_driver'],
                         eta_antenna=bb['eta_antenna']))
    print()

    print('=== all four lengths, RSENSE = 10 ===')
    print('%8s %9s %10s %9s %12s %11s' % ('len_cm', 'Rt', 'coilR', 'antR', 'eta_driver%', 'eta_ant%'))
    per_len = []
    for a in ants:
        bb = budget(a)
        print('%8d %9.3f %10.3f %9.3f %12.2f %11.2f'
              % (round(a['length_m'] * 100), bb['Rt'], bb['parts']['COIL'],
                 bb['parts']['ANTENNA_LOSS'], 100 * bb['eta_driver'], 100 * bb['eta_antenna']))
        per_len.append(dict(length_cm=round(a['length_m'] * 100), **{k: v for k, v in bb.items() if k != 'parts'}))

    b90 = budget(d90)
    (ROOT / 'loss_budget.json').write_text(json.dumps(dict(
        note='All resistances port-referred; sum equals joint_sim port resistance.',
        parts90=b90['parts'], budget90={k: v for k, v in b90.items() if k != 'parts'},
        rsense_sweep=rows, per_length=per_len), indent=2), encoding='utf-8')
    print('\nwritten loss_budget.json')


if __name__ == '__main__':
    main()
