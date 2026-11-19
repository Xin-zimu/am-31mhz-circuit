"""Field strength and link budget for the 31 MHz AM link at 6 m.

Everything here is an estimate from antenna theory plus the AM-ALT.2 measured
transmitter currents. It is NOT a measurement and NOT a substitute for the 6 m
test the course requires -- the report states that plainly.

*** CORRECTED 2026-11-16 (P1b). This script previously used h_eff = h/2 for the
*** RECEIVE antenna, which the errata in 02_AM-ALT.3_勘误与天线阻抗测量方案.md
*** proved is wrong: a monopole over a ground plane sees the image, so the
*** open-circuit voltage against the incident field is V_oc = E * h, not E * h/2.
*** Taking h/2 understates h_eff by 2x, which doubles the required field and
*** therefore doubles the required antenna current. The reciprocity check makes
*** this conclusive: D = 3 requires A_em = 3*lambda^2/(4*pi) = 22.30 m^2, and
*** A_em = eta0*h_eff^2/(4*R_rad) then forces h_eff = h. Using h/2 implies
*** D = 0.749 < 1, which no antenna can achieve.
***
*** The historical (uncorrected) numbers are still reproducible on purpose by
*** `scripts/link_budget_audit.py`, which recreates both defects separately and
*** attributes them: defect A (h/2) is x2.000, defect B (rms divided by sqrt 2
*** again) is x0.707, net x1.414. Do not "fix" that file -- it is the audit.

Short-monopole relations used (h << lambda, triangular current):
    R_rad   = 395 * (h/lambda)^2                        [ohm]
    h_eff   = h                                         [m]  (transmit and receive;
                                                              ground-plane image included)
    E_max   = sqrt(180 * P_rad) / r                     [V/m] at the horizon
    V_oc    = E * h_eff                                 [V]  at the receive antenna

E_max = sqrt(180 P)/r follows from S_max = E^2/(2*eta0) on a sin^2(theta) pattern
over a hemisphere: P = (4*pi*r^2/3) * S_max = r^2 * E_max^2 / 180.
"""
import numpy as np
from antenna_model import (C0, F, LAM, schelkunoff, efficiency,
                           radiation_resistance)

ETA0 = 376.730313668
H_TX = 1.00          # m, at the course limit
A_WIRE = 0.5e-3      # m, wire radius


def h_eff_monopole(h):
    """Effective height of a monopole above a ground plane [m].

    The ground-plane image doubles the tangential field at the antenna, so the
    open-circuit voltage against the incident field is E*h. See the module
    docstring for the reciprocity argument that forces this.
    """
    return h


def e_max_from_power(p_avg, r):
    """Peak E at distance r from an AVERAGE radiated power p_avg [W].

    P = r^2 E_peak^2 / 180, so E_peak = sqrt(180 P)/r. The 180 already folds in
    the 1/2 from time-averaging (S_avg = E_peak^2/(2 eta0)) and the hemisphere
    pattern integral (4*pi/3). Feeding a PEAK power here would double the
    argument and overstate E by sqrt(2) -- that was a latent defect in this
    script, fixed in the same pass as h_eff; see the module docstring.
    """
    return np.sqrt(180.0 * p_avg) / r


def field_from_current(i_peak, h=H_TX, r=6.0):
    """Peak E at distance r, for a short monopole carrying i_peak at the base.

    Returns (E_peak, P_avg). The power must be time-averaged before it goes
    into the far-field relation: p_avg = i_peak^2 * R_rad / 2.
    """
    p_avg = i_peak ** 2 * radiation_resistance(h) / 2.0
    return e_max_from_power(p_avg, r), p_avg


def link(i_ant_peak, h_tx=H_TX, h_rx=1.00, r=6.0):
    e, p_rad = field_from_current(i_ant_peak, h_tx, r)
    v_oc = e * h_eff_monopole(h_rx)          # was: e * (h_rx / 2)  -- see docstring
    return {"I_ant_peak_mA": i_ant_peak * 1e3,
            "P_rad_uW": p_rad * 1e6,
            "E_at_r_mV_per_m": e * 1e3,
            "V_oc_rx_mV_peak": v_oc * 1e3}


if __name__ == "__main__":
    print(f"31 MHz  lambda={LAM:.3f} m   TX/RX monopole h={H_TX:.2f} m "
          f"({H_TX/LAM:.3f} lambda)   distance 6 m")
    print()

    print("=== 1. antenna impedance and efficiency at the chosen height ===")
    Rr, X = schelkunoff(H_TX, A_WIRE)
    print(f"    R_rad = {Rr:.3f} ohm,  X = {X:.1f} ohm,  |X|/R_rad = {abs(X)/Rr:.0f}")
    for q in (30, 60, 100):
        e = efficiency(H_TX, A_WIRE, coil_q=q, r_ground=1.0)
        print(f"    coil Q={q:3d}:  L_tune={e['L_tune_nH']:.0f} nH  "
              f"R_coil={e['R_coil']:5.2f} ohm  R_total={e['R_total']:6.2f} ohm  "
              f"efficiency={e['efficiency_pct']:5.1f}%")
    print()

    print("=== 2. what the AM-ALT.2 output stage can actually deliver ===")
    # QOB emitter follower: 33k/33k bias from 5 V, 330 ohm emitter resistor.
    v_b = 2.5
    v_e = v_b - 0.7
    i_bias = v_e / 330.0
    r_out_follower = 1.0 / (1.0 / 330.0 + 1.0 / (16500.0 / 416.4 + 0.026 / i_bias))
    print(f"    QOB bias: V_E={v_e:.2f} V, I_E={i_bias*1e3:.2f} mA")
    print(f"    follower output resistance ~{r_out_follower:.1f} ohm")
    print(f"    ROISO 1 kohm in series -> source ~{r_out_follower + 1000:.0f} ohm")
    print("    peak AC current available before cut-off: ~"
          f"{i_bias*1e3:.1f} mA (class A, so the bias current is the ceiling)")
    print()

    print("=== 3. field at 6 m for a range of antenna currents ===")
    print(f"{'I_ant/mA':>9} {'P_rad/uW':>10} {'E/(mV/m)':>10} {'V_oc_rx/mV':>11}")
    for i_ma in (1.0, 2.0, 4.0, 5.0, 8.0, 12.0, 20.0, 40.0):
        r = link(i_ma * 1e-3)
        print(f"{r['I_ant_peak_mA']:9.1f} {r['P_rad_uW']:10.3f} "
              f"{r['E_at_r_mV_per_m']:10.2f} {r['V_oc_rx_mV_peak']:11.2f}")
    print()
    print("    reference: the S05 receiver was designed around a 10 mV open-circuit")
    print("    peak at the antenna terminals (50 ohm source).")
    print()

    print("=== 4. does the existing stage reach that, with and without a driver ===")
    eth = efficiency(H_TX, A_WIRE, coil_q=60, r_ground=1.0)
    for label, i_peak in (("existing 5.5 mA bias", 5.0e-3),
                          ("bias doubled to 11 mA", 10.0e-3),
                          ("20 mA driver", 18.0e-3)):
        r = link(i_peak)
        v_ant = i_peak * eth["R_total"]
        print(f"    {label:24} I={i_peak*1e3:5.1f} mA  "
              f"V_ant={v_ant:5.2f} Vpk  E={r['E_at_r_mV_per_m']:5.1f} mV/m  "
              f"V_oc_rx={r['V_oc_rx_mV_peak']:5.1f} mV")
    print()
    print("    注意：V_ant 是天线端口的峰值电压，必须小于输出级的可用摆幅；")
    print("    现有射随在 5 V 供电下约 ±1.5 V，因此 18 mA 档需要重新核算摆幅。")
    print()

    print("=== 5. loaded bandwidth vs the 20 kHz AM sidebands ===")
    xl = abs(X)
    r_total = eth["R_total"]
    q_loaded = xl / r_total
    bw = F / q_loaded
    print(f"    series-tuned: Q_loaded = |X|/R_total = {q_loaded:.1f}")
    print(f"    bandwidth = f/Q = {bw/1e3:.0f} kHz")
    print(f"    AM sidebands at +/-20 kHz -> ratio {20e3/(bw/2):.3f} of half-BW")
    print(f"    -> the carrier and both sidebands fit inside the tuned band "
          f"({'OK' if bw/2 > 3*20e3 else 'MARGINAL'})")
    print()
    print("    这是本阶段一个重要结论：加入线圈损耗后加载Q远低于天线自身Q，")
    print("    20 kHz 边带不会因天线窄带而被削掉。代价是效率，不是带宽。")
