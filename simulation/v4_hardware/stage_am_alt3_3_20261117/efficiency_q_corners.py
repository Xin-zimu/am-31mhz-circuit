"""Efficiency uncertainty and Q-corner transients. No hardware claims.

1) A reproducible table of bare-port and matched space-wave efficiency spread over the
   geometry/environment/material scenarios already solved by model_whip.py, plus the
   216-case analytic parasitic scan.
2) Transient Q corners under the frozen driver: the manufacturer typical model (Q31=59.7)
   is OPTIMISTIC relative to the datasheet guarantee (Q>=63 @ 50 MHz). Re-solving the
   Document 158 model for Q50=63 gives loss_scale=1.2646 and Q31=47.3. Both sides of the
   typical value are run so the sweep is not one-directional.
"""
import csv, json, math, statistics
from joint_sim import ROOT, PART, coil, ant, design, W, execute
import joint_sim as sim

LOSS_MIN_Q50_63 = 1.2646  # solved from Document 158 model: Q(50MHz)=63 (datasheet minimum)
LOSS_HIGH_Q = 0.5         # optimistic high-Q side, Q31 ~ 119


def efficiency_uncertainty():
    ants = json.loads((ROOT / 'antenna_all.json').read_text(encoding='utf-8'))
    # Bare-port efficiency across material/environment scenarios (no matching, no 10 ohm).
    scen = ['thin', 'nom', 'thick', 'copper', 'dry', 'wet']
    rows = []
    for L in sorted({r['length_m'] for r in ants}):
        g = {r['label']: r['radiated_fraction'] for r in ants if r['length_m'] == L}
        v = [100 * g[s] for s in scen]
        rows.append(dict(kind='bare_port', length_cm=round(L * 100), n=len(v),
                         min_pct=min(v), max_pct=max(v), span_pp=max(v) - min(v),
                         ratio=max(v) / min(v), median_pct=statistics.median(v),
                         scenarios=' '.join(scen)))
    # Matched efficiency across the 216-case analytic parasitic scan.
    scan = list(csv.DictReader((ROOT / 'retune_sensitivity.csv').open(encoding='utf-8-sig')))
    for L in sorted({float(r['length_m']) for r in scan}):
        v = sorted(100 * float(r['efficiency_with_sense']) for r in scan if float(r['length_m']) == L)
        rows.append(dict(kind='matched_with_10ohm', length_cm=round(L * 100), n=len(v),
                         min_pct=v[0], max_pct=v[-1], span_pp=v[-1] - v[0], ratio=v[-1] / v[0],
                         median_pct=statistics.median(v),
                         scenarios='Lscale x extraCp x baseC x loss'))
    with (ROOT / 'efficiency_uncertainty.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r['kind'], r['length_cm'], round(r['min_pct'], 2), round(r['max_pct'], 2),
              'ratio', round(r['ratio'], 2), flush=True)
    return rows


def q_table():
    """Q31 vs loss_scale for the 4.7 uH model, so the sweep direction is explicit."""
    rows = []
    for loss in [0.5, 0.7, 1.0, 1.2646, 1.5, 2.0, 3.0]:
        z = coil(loss=loss)
        rows.append(dict(loss_scale=loss, Q31=z.imag / z.real, coil_R31_ohm=z.real,
                         label='typical' if loss == 1.0 else
                               ('datasheet_min_Q50_63' if abs(loss - 1.2646) < 1e-6 else
                                ('optimistic_highQ' if loss < 1 else 'lowQ_stress'))))
    with (ROOT / 'q_corners.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r['label'], round(r['loss_scale'], 4), 'Q31=', round(r['Q31'], 1), flush=True)
    return rows


def main():
    efficiency_uncertainty()
    q_table()
    # Transient corners around the typical Q; CT is essentially loss-independent
    # (required C = 14.289 pF for every loss scale), so each case stays on resonance.
    execute((.9, 'Qmin50m63', .25, 1, LOSS_MIN_Q50_63, 0, .2, .5e-12, 1, 1))
    execute((.9, 'Qhigh119', .25, 1, LOSS_HIGH_Q, 0, .2, .5e-12, 1, 1))


if __name__ == '__main__':
    main()
