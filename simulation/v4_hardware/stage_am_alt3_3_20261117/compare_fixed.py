"""Purchased fixed RF inductors vs radiator length: analytic coverage + transient checks.

All three parts are Coilcraft 1812CS with manufacturer SPICE typical models (Document 158),
so none of these numbers is an ideal high-Q assumption. Same frozen driver as joint_sim.
"""
import json, math, csv
from joint_sim import ROOT, OUT, PART, W, coil, ant, design, execute
import joint_sim as sim

# Coilcraft Document 158 typical models: R2 + ((Rskin + jwL) || (R1 + 1/jwCp))
PARTS = {
    '1812CS-472': dict(R1=85.,  R2=5.4, Cp=.122e-12, L=4.775e-6, k=.00180),  # 4.7 uH
    '1812CS-392': dict(R1=121., R2=5.0, Cp=.118e-12, L=3.950e-6, k=.00112),  # 3.9 uH
    '1812CS-332': dict(R1=81.,  R2=3.8, Cp=.120e-12, L=3.330e-6, k=.00112),  # 3.3 uH
}
TRIM_MIN, TRIM_MAX = 2e-12, 18e-12  # Vishay BFC280905217


def coverage(part):
    """Required series C at 31 MHz and whether the trimmer alone can reach it."""
    p = PARTS[part]
    sim.PART = p
    rows = []
    for d in json.loads((ROOT / 'antenna_nominal.json').read_text(encoding='utf-8')):
        z, za = coil(), ant(d)
        x = (z + za).imag + W * 2e-9
        c = 1 / (W * x) if x else float('inf')
        capr = .0025 / (W * c) if c > 0 else 0.0
        rows.append(dict(
            part=part, length_cm=round(d['length_m'] * 100),
            required_total_C_pF=c * 1e12,
            series_C_required=('capacitor' if c > 0 else 'inductor'),
            coil_R31_ohm=z.real, coil_X31_ohm=z.imag, Q31=z.imag / z.real,
            port_R_with_10ohm=10 + z.real + za.real + capr,
            trim_alone=bool(TRIM_MIN <= c <= TRIM_MAX),
            trim_plus_fixed_C0G=bool(c > TRIM_MAX),
        ))
    return rows


def main():
    # 1) Analytic coverage of every part over the four lengths (216-case scan is separate).
    allrows = []
    for part in PARTS:
        allrows += coverage(part)
    with (ROOT / 'fixed_inductor_coverage.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, allrows[0].keys()); w.writeheader(); w.writerows(allrows)
    print('coverage rows', len(allrows), flush=True)

    # 2) Transient joint checks under the frozen driver, newly tuned for each part.
    sim.PART = PARTS['1812CS-472']
    execute((.9, 'opt472', .25, 1, 1, 0, .2, .5e-12, 1, 1))
    sim.PART = PARTS['1812CS-392']
    execute((.9, 'opt392', .25, 1, 1, 0, .2, .5e-12, 1, 1))
    sim.PART = PARTS['1812CS-332']
    execute((.9, 'opt332', .25, 1, 1, 0, .2, .5e-12, 1, 1))


if __name__ == '__main__':
    main()
