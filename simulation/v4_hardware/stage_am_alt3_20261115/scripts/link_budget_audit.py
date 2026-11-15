"""Audit the AM-ALT.3 link budget and recompute the antenna-current requirement.

Why this file exists
--------------------
requirement.py concluded the TX must deliver **5.30 mA rms** of antenna current to
give v2 >= 4 Vpp at 6 m. That number drove the decision to add a two-transistor
driver stage, and the report then claimed the driver reaches "118%" of it. Both
the number and the margin claim are re-derived here.

Defect A -- receiving effective height omits the ground-plane image
    requirement.py uses h_eff_rx = h/2 = 0.50 m, the free-space short-monopole
    effective height. A monopole over a ground plane is not in free space: the
    image doubles the tangential field at the antenna, so the open-circuit
    voltage referred to the *incident* field is

        V_oc = E_inc * h      (h_eff = h),   not E_inc * h/2.

    This is forced by reciprocity, independently of the integral: the same
    antenna has D = 3, hence A_em = 3*lambda^2/(4*pi) = 22.3 m^2, and
    A_em = eta0*h_eff^2/(4*R_rad) then REQUIRES h_eff = h (see
    aperture_consistency()). h_eff = h/2 would imply D = 0.75 < 1, which no
    antenna can have. Using h/2 demands twice the field, hence 2x the current.

Defect B -- a time-averaged power turned into a "peak" current, then divided again
    radiated_power_needed() computes P = E_peak^2 * r^2 / 180. That 180 is
    correct for time-averaged power with G = 3 and a PEAK field:

        P_avg = S_avg * 4*pi*r^2 / G,   S_avg = E_peak^2 / (2*eta0)
              = E_peak^2 * r^2 * 2*pi / (eta0*G)  =  E_peak^2 * r^2 / 180  for G = 3.

    So P is an average power, and I = sqrt(P/R_rad) = 7.495 mA is therefore
    already the RMS current. requirement.py labels that same number "peak"
    (i_ant_needed_mA_peak = 7.495) and then reports rms = 7.495/sqrt(2) =
    5.30 mA. Dividing an rms current by sqrt(2) a second time understates the
    requirement of its own model by sqrt(2).

    Consequence for the margin claim: comparing the ngspice *rms* antenna
    current (6.250 mA) against a requirement that had been divided by sqrt(2)
    is not a like-for-like comparison. Against its own model's rms requirement
    the driver reaches 6.250/7.495 = 83%, not 118%.

The net error, and why it must still be recorded
    The two defects act in opposite directions: A inflates by 2, B deflates by
    sqrt(2), net sqrt(2). Correcting both gives **3.75 mA rms** at ideal D = 3.

    Twisting the story: the published 5.30 mA rms equals the CORRECTLY computed
    value for the pessimistic directivity D = 1.5 (3.749 * sqrt(3/1.5) = 5.302).
    So the target the project has been designing against is not dangerous -- it is
    the worst-case end of the honest bracket, D between 1.5 and 3 -- but that is a
    numerical accident, not an argument, and the published derivation cannot be
    reproduced as written. Record the error AND the coincidence.

What does NOT change
    The driver is still justified: every point of the D bracket (3.75-5.30 mA rms)
    exceeds the existing output stage's hard ceiling (1.19 mA rms) by 3.1x-4.4x,
    and the driver's 6.25 mA covers the whole bracket (112%-167%).

    What IS invalid is the report's "118% of requirement" margin: it divides an
    ngspice rms current by a requirement already divided by sqrt(2). Against its
    own model's rms requirement the driver is 83%.

    The receiver voltage-to-v2 chain (S05's 10 mV -> 4.777 Vpp at m = 0.50, and
    the m-scaling) is taken as a measured input and is not re-derived here.

This is an estimate, and NOT a substitute for measurement: at 31 MHz, r = 6 m is
r/lambda = 0.62, i.e. inside the near field, where the far-field power-density
argument this whole budget rests on is not strictly valid. Hence the bracket and
hence the insistence that 6 m must be measured.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

C0 = 299792458.0
F = 31e6
LAM = C0 / F
ETA0 = 376.730313668
H = 1.00                      # monopole height, m
R_GROUND = 1.0                # ground loss, ohm
COIL_Q = 60.0
DIST = 6.00
G_TX = 3.0                    # short monopole over ground plane, D = 3 (6 dB)

R_RAD = 395.0 * (H / LAM) ** 2

# measured receiver chain (S05-06 / AM-ALT.2), not re-derived here
V2_PER_MV_AT_M05 = 4.7770 / 10.0     # Vpp per mV of open-circuit peak, at m = 0.50
M_S05 = 0.50
M_ALT2 = 0.2431
V2_REQUIRED = 4.0

CEILING_MA = 1.1924907996317227      # AM-ALT.3 existing-output hard ceiling, mA rms
DRIVER_MA = 6.249898162776399        # ngspice fin_nom, mA rms


def aperture_consistency():
    """Show that h_eff = h/2 contradicts D = 3 for this very antenna."""
    checks = []
    for label, h_eff in (("h/2 (free space)", H / 2), ("h (with image)", H)):
        a_em = ETA0 * h_eff ** 2 / (4 * R_RAD)
        d = 4 * math.pi * a_em / LAM ** 2
        checks.append({"convention": label, "h_eff_m": h_eff,
                       "A_em_m2": a_em, "implied_D": d,
                       "physically_possible": d >= 1.0})
    a_for_d3 = G_TX * LAM ** 2 / (4 * math.pi)
    return {
        "checks": checks,
        "A_em_for_D3_m2": a_for_d3,
        "h_eff_required_by_D3_m": math.sqrt(4 * R_RAD * a_for_d3 / ETA0),
        "note": ("h_eff = h/2 implies D = 0.75 < 1, impossible for any antenna. "
                 "The monopole over a ground plane has D = 3, which forces "
                 "h_eff = h. The image doubles the tangential field."),
    }


def required_voc_mv(m=M_ALT2, target=V2_REQUIRED):
    """Open-circuit peak needed at the RX antenna for v2 >= target."""
    return target / (V2_PER_MV_AT_M05 * (m / M_S05))


def chain(voc_mv, h_eff):
    """Open-circuit peak -> E_peak -> S_avg -> P_avg -> I_rms (all consistent)."""
    e_peak = voc_mv * 1e-3 / h_eff
    s_avg = e_peak ** 2 / (2 * ETA0)
    p_avg = s_avg * 4 * math.pi * DIST ** 2 / G_TX
    i_rms = math.sqrt(p_avg / R_RAD)
    return {
        "h_eff_m": h_eff,
        "E_peak_mV_per_m": e_peak * 1e3,
        "E_rms_mV_per_m": e_peak / math.sqrt(2) * 1e3,
        "S_avg_W_per_m2": s_avg,
        "P_avg_uW": p_avg * 1e6,
        "I_rms_mA": i_rms * 1e3,
        "I_peak_mA": i_rms * math.sqrt(2) * 1e3,
    }


def chain_with_directivity(voc_mv, d_tx, h_eff=H):
    """Same chain, but with the transmitter directivity as a free parameter.

    Note the receiving side does NOT get a matching directivity factor here: the
    open-circuit voltage is fixed by h_eff, which is already a property of the
    receiving antenna in its own environment. Only the TX side enters via D_tx.
    """
    e_peak = voc_mv * 1e-3 / h_eff
    s_avg = e_peak ** 2 / (2 * ETA0)
    p_avg = s_avg * 4 * math.pi * DIST ** 2 / d_tx
    i_rms = math.sqrt(p_avg / R_RAD)
    return {"directivity": d_tx, "P_avg_uW": p_avg * 1e6, "I_rms_mA": i_rms * 1e3}


def efficiency():
    xl = 576.035515515845
    r_coil = xl / COIL_Q
    r_total = R_RAD + r_coil + R_GROUND
    return {"R_coil_ohm": r_coil, "R_total_ohm": r_total,
            "efficiency_pct": 100 * R_RAD / r_total}


def main():
    out = {
        "frequency_Hz": F,
        "lambda_m": LAM,
        "r_over_lambda": DIST / LAM,
        "fraunhofer_2D2_over_lambda_m": 2 * H ** 2 / LAM,
        "R_rad_ohm": R_RAD,
        "G_tx": G_TX,
    }
    out["aperture_consistency"] = aperture_consistency()

    voc = required_voc_mv()
    out["required_voc_mV_peak"] = voc

    # Reproduce requirement.py exactly, then relabel consistently.
    published_model = chain(voc, H / 2)          # their h_eff = h/2
    out["published_model_consistent_rms_mA"] = published_model["I_rms_mA"]
    out["published_reported_rms_mA"] = published_model["I_rms_mA"] / math.sqrt(2)
    out["published_P_uW"] = published_model["P_avg_uW"]
    out["published_E_peak_mV_per_m"] = published_model["E_peak_mV_per_m"]
    out["published_labels_as_in_report"] = {"peak_mA": published_model["I_rms_mA"],
                                            "rms_mA": published_model["I_rms_mA"] / math.sqrt(2)}

    corrected = chain(voc, H)                    # h_eff = h
    out["corrected"] = corrected

    out["attribution"] = {
        "defect_A_h_eff": {
            "published_h_eff_m": H / 2, "correct_h_eff_m": H,
            "current_factor": 2.0,
            "effect": "inflates the requirement by 2x",
        },
        "defect_B_peak_rms": {
            "published_states_rms_mA": out["published_reported_rms_mA"],
            "its_own_model_rms_mA": published_model["I_rms_mA"],
            "current_factor": 1 / math.sqrt(2),
            "effect": "understates its own model's rms requirement by sqrt(2)",
        },
        "net": {
            "published_stated_rms_mA": out["published_reported_rms_mA"],
            "corrected_rms_mA": corrected["I_rms_mA"],
            "overstatement_factor": out["published_reported_rms_mA"] / corrected["I_rms_mA"],
            "consistent_with": "2 / sqrt(2) = sqrt(2)",
        },
    }

    eff = efficiency()
    out["efficiency"] = eff
    i_rms = corrected["I_rms_mA"] / 1e3
    out["port"] = {
        "P_port_uW": corrected["P_avg_uW"] / (eff["efficiency_pct"] / 100),
        "V_port_mV_rms": i_rms * eff["R_total_ohm"] * 1e3,
    }

    out["gap"] = {
        "corrected_need_mA_rms": corrected["I_rms_mA"],
        "published_need_mA_rms": out["published_reported_rms_mA"],
        "ceiling_mA_rms": CEILING_MA,
        "corrected_gap_ratio": corrected["I_rms_mA"] / CEILING_MA,
        "published_gap_ratio": out["published_reported_rms_mA"] / CEILING_MA,
    }

    out["driver_margin"] = {
        "simulated_rms_mA": DRIVER_MA,
        "vs_corrected_need_pct": 100 * DRIVER_MA / corrected["I_rms_mA"],
        "vs_published_claim_pct": 100 * DRIVER_MA / out["published_reported_rms_mA"],
        "vs_its_own_model_rms_pct": 100 * DRIVER_MA / published_model["I_rms_mA"],
        "note": ("the report's 118% mixes an ngspice rms current against a "
                 "requirement that had been divided by sqrt(2); against its own "
                 "model it is 83%. Against the corrected model it is 167%."),
    }

    # Honest bracket. The dominant uncertainty is the receiving effective height,
    # which is a genuine convention question, and the directivity of a 0.103-lambda
    # monopole over a FINITE ground plane (the TX chassis, not an infinite sheet).
    # I scales as 1/sqrt(D), not 1/D, because D enters through the required power.
    bracket = []
    for d in (3.0, 2.0, 1.5):
        c = chain_with_directivity(voc, d)
        bracket.append({"directivity": d, "dBi": 10 * math.log10(d),
                        "I_rms_mA": c["I_rms_mA"], "P_avg_uW": c["P_avg_uW"]})
    out["bracket_by_directivity"] = {
        "rows": bracket,
        "scaling": "I scales as 1/sqrt(D)",
        "I_low_mA": bracket[0]["I_rms_mA"],
        "I_high_mA": bracket[-1]["I_rms_mA"],
        "driver_meets_D": [
            {"directivity": d, "met": DRIVER_MA >= r["I_rms_mA"]}
            for d, r in zip((3.0, 2.0, 1.5), bracket)
        ],
        "note": ("A real 1 m monopole over a transmitter chassis sits between "
                 "D = 1.5 and D = 3, so the requirement is %.2f to %.2f mA rms "
                 "and the ideal D = 3 value is a lower bound."
                 % (bracket[0]["I_rms_mA"], bracket[-1]["I_rms_mA"])),
    }

    out["conclusion"] = {
        "finding": (
            "the published 5.30 mA rms figure is derived by two convention defects "
            "that act in opposite directions: h_eff = h/2 instead of h (inflates "
            "the field and hence the current by 2x) and an already-rms current "
            "labelled 'peak' then divided by sqrt(2) (deflates by sqrt2). Net "
            "sqrt(2). The single defensible value is 3.75 mA rms at ideal D = 3"),
        "important_twist": (
            "5.30 mA rms happens to equal the correctly-computed value for the "
            "PESSIMISTIC directivity D = 1.5 (3.749 * sqrt(3/1.5) = 5.302). So the "
            "number the project has been designing against is not dangerous -- it "
            "is the worst-case end of the honest bracket -- but it was reached by "
            "accident, not by argument, and the published derivation cannot be "
            "reproduced. The error and its cancellation must both be recorded"),
        "does_it_change_the_driver_decision": (
            "no. Every point in the D bracket (3.75 to 5.30 mA rms) exceeds the "
            "existing output ceiling of 1.19 mA rms by 3.1x to 4.4x, so a driver "
            "stage is justified either way. The driver's 6.25 mA rms covers the "
            "whole bracket (112% to 167%)"),
        "what_is_still_invalid": (
            "the reported '118% of requirement' margin is not a sound comparison: "
            "it divides an ngspice rms current by a requirement that had already "
            "been divided by sqrt(2), and against its own model's rms requirement "
            "the driver is 83%. The margin must be restated against the corrected "
            "bracket (112%-167%), not against the accidental 5.30"),
        "must_still_be_measured": (
            "at 31 MHz, r = 6 m is r/lambda = 0.62, inside the near field, where "
            "the far-field power-density argument is not strictly valid and "
            "ground-plane and near-field effects dominate. No link budget -- "
            "corrected or not -- can settle 6 m; it must be measured"),
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "link_budget_audit.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- stdout summary ----
    print(f"lambda = {LAM:.4f} m,  r/lambda = {DIST/LAM:.3f}  "
          f"(Fraunhofer 2D^2/lambda = {2*H**2/LAM:.2f} m)")
    print(f"R_rad = {R_RAD:.4f} ohm,  G_tx = {G_TX:.0f} (D = 4.77 dBi)")
    print()
    print("=== aperture consistency: the two conventions cannot both be right ===")
    for c in out["aperture_consistency"]["checks"]:
        print(f"  {c['convention']:18} h_eff={c['h_eff_m']:.2f} m -> "
              f"A_em={c['A_em_m2']:6.2f} m2 -> implied D={c['implied_D']:5.3f}  "
              f"possible={c['physically_possible']}")
    print(f"  D={G_TX:.0f} requires h_eff = {out['aperture_consistency']['h_eff_required_by_D3_m']:.3f} m")
    print()
    print("=== the requirement, three ways ===")
    print(f"  V_oc needed (carrier peak) = {voc:.4f} mV   (unchanged)")
    print(f"  {'':28}{'E_pk mV/m':>11}{'P_avg uW':>11}{'I_rms mA':>11}{'I_pk mA':>10}")
    row = f"  {'published (h_eff=h/2)':28}{published_model['E_peak_mV_per_m']:11.2f}" \
          f"{published_model['P_avg_uW']:11.2f}{published_model['I_rms_mA']:11.3f}" \
          f"{published_model['I_peak_mA']:10.3f}"
    print(row)
    row = f"  {'corrected (h_eff=h)':28}{corrected['E_peak_mV_per_m']:11.2f}" \
          f"{corrected['P_avg_uW']:11.2f}{corrected['I_rms_mA']:11.3f}" \
          f"{corrected['I_peak_mA']:10.3f}"
    print(row)
    print()
    print("=== defect attribution ===")
    a = out["attribution"]
    print(f"  A. h_eff = h/2 instead of h        -> x{a['defect_A_h_eff']['current_factor']:.3f} (inflates)")
    print(f"  B. rms labelled peak, then /sqrt2  -> x{a['defect_B_peak_rms']['current_factor']:.3f} (deflates)")
    n = a["net"]
    print(f"  net: reported {n['published_stated_rms_mA']:.2f} vs corrected "
          f"{n['corrected_rms_mA']:.2f} mA rms -> x{n['overstatement_factor']:.3f}")
    print()
    print("=== consequence for the driver decision ===")
    g, d = out["gap"], out["driver_margin"]
    print(f"  corrected need {g['corrected_need_mA_rms']:.3f} mA rms vs ceiling "
          f"{g['ceiling_mA_rms']:.3f} -> gap x{g['corrected_gap_ratio']:.2f} "
          f"(published x{g['published_gap_ratio']:.2f})")
    print(f"  driver {d['simulated_rms_mA']:.2f} mA rms:")
    print(f"     vs corrected requirement : {d['vs_corrected_need_pct']:5.0f}%")
    print(f"     vs report's own model rms: {d['vs_its_own_model_rms_pct']:5.0f}%  <- apples-to-apples")
    print(f"     vs report's stated 5.30  : {d['vs_published_claim_pct']:5.0f}%  <- the 118% claim")
    print()
    b = out["bracket_by_directivity"]
    print(f"  requirement bracket vs directivity (I scales as 1/sqrt(D)):")
    for row, met in zip(b["rows"], b["driver_meets_D"]):
        mark = "OK " if met["met"] else "SHORT"
        print(f"     D={row['directivity']:4.1f} ({row['dBi']:5.2f} dBi) -> "
              f"{row['I_rms_mA']:5.2f} mA rms   driver 6.25 mA: {mark}")
    print(f"     => corrected 3.75 mA is a LOWER BOUND. NOTE: 5.30 mA is exactly D=1.5;")
    print()
    print(f"  efficiency = {eff['efficiency_pct']:.1f}%  (R_total = {eff['R_total_ohm']:.2f} ohm)")
    print("written:", RESULTS / "link_budget_audit.json")


if __name__ == "__main__":
    main()
