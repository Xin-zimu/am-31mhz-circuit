"""Fixed-length comparison: which 1812CS is best if we only need 90-100 cm?

Reviewer's point: the antenna is tuned once at installation, not swept 70->100 cm daily.
So 'one trimmer covers every length' is not a requirement worth paying efficiency for.
This compares the three parts within the trimmer's own 2-18 pF range at 90 and 100 cm,
and states exactly what extra capacitance each option needs.
"""
import json, csv, math
import joint_sim as s

W = s.W
PARTS = {
    '1812CS-332': dict(R1=81.,  R2=3.8, Cp=.120e-12, L=3.330e-6, k=.00112, L_nom=3.3),
    '1812CS-392': dict(R1=121., R2=5.0, Cp=.118e-12, L=3.950e-6, k=.00112, L_nom=3.9),
    '1812CS-472': dict(R1=85.,  R2=5.4, Cp=.122e-12, L=4.775e-6, k=.00180, L_nom=4.7),
}
TRIM = (2e-12, 18e-12)
ants = json.loads((s.ROOT / 'antenna_nominal.json').read_text(encoding='utf-8'))


def analyse(part, d):
    s.PART = {k: v for k, v in PARTS[part].items() if k != 'L_nom'}
    z, za = s.coil(), s.ant(d)
    c = 1 / (W * ((z + za).imag + W * 2e-9))
    capr = .0025 / (W * c)
    rt = 10 + z.real + za.real + capr
    radz = (d['R'] + .2) + 1j * (W * d['Lant_H'] - 1 / (W * d['Cant_F']))
    ratio2 = abs(1 + 1j * W * .5e-12 * radz) ** 2
    eta = d['R_radiated'] / (ratio2 * rt)
    eta_ant = d['R_radiated'] / (ratio2 * (rt - 10))
    return dict(part=part, length_cm=round(d['length_m'] * 100),
                C_pF=c * 1e12, trim_alone=bool(TRIM[0] <= c <= TRIM[1]),
                extra_C0G_pF=max(0.0, (c * 1e12) - 18.0) if c * 1e12 > 18 else 0.0,
                Q31=z.imag / z.real, coilR=z.real, Rt=rt,
                eta_driver=eta, eta_antenna=eta_ant)


def main():
    rows = []
    for part in PARTS:
        for d in ants:
            if round(d['length_m'] * 100) in (90, 100):
                rows.append(analyse(part, d))
    with (s.ROOT / 'fixed_length_part_choice.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    print('%-13s %4s %9s %9s %8s %11s %11s %10s'
          % ('part', 'len', 'C_pF', 'extraC0G', 'Q31', 'eta_drv%', 'eta_ant%', 'trim_only'))
    for r in rows:
        print('%-13s %4d %9.3f %9.1f %8.1f %11.3f %11.3f %10s'
              % (r['part'], r['length_cm'], r['C_pF'], r['extra_C0G_pF'], r['Q31'],
                 100 * r['eta_driver'], 100 * r['eta_antenna'], r['trim_alone']))
    print('\nwritten fixed_length_part_choice.csv')


if __name__ == '__main__':
    main()
