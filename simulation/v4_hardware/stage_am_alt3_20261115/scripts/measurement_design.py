"""Design and error-budget the antenna-impedance measurement (AM-ALT.3, bench step).

The AM-ALT.3 report answers "what antenna" (1.00 m vertical monopole) but leaves
"what impedance does it present at 31 MHz" as a formula estimate of 8.91 pF. This
script does not measure anything. It computes, for the equipment actually owned
(Rigol DS2102E + signal generator + DMM, no LCR meter / no VNA), whether the
series-resonance method can measure that capacitance to a useful accuracy, and
what the scope should display at each step.

Method
------
    generator --[ R_sense ]--[ L ]--+-- antenna (C_ant to chassis) --+
                                    |                              |
                                   GND --------------------------

Sweep the generator frequency and find the series resonance: the frequency at
which the current through the loop peaks, i.e. the voltage across R_sense peaks.
At resonance the loop is purely resistive, so

    C_total = 1 / ( (2*pi*f_res)^2 * L )
    C_ant   = C_total - C_stray
    R_side  = V_emf / I_res - R_gen - R_sense        (loss resistance, ohm)

Unknown L is a problem, because C scales as 1/L: a 5% L error is a 5% C error.
L is measured by resonating it against two *known* capacitors and eliminating the
unknown stray capacitance:

    1/(w1^2 L) = Cf1 + Cs
    1/(w2^2 L) = Cf2 + Cs
    =>  L = (1/w1^2 - 1/w2^2) / (Cf1 - Cf2)

This cancels Cs exactly but amplifies capacitor tolerance, because it depends on
the *difference* Cf1 - Cf2. The script quantifies that, which is the reason the
procedure insists on a large capacitance step and a low test frequency.

Everything printed here is a design target for the bench, not a result.
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

C0 = 299792458.0
F = 31e6
PROBE_PF = 16.0          # DS2102E 10x passive probe, tip capacitance
R_GEN = 50.0             # generator source resistance, ohm
R_SENSE = 10.0           # current-sense resistor, ohm

# model values the bench result will be compared against
C_MODEL_PF = 8.913
R_SIDE_MODEL = 13.824    # R_rad 4.224 + R_coil 9.6 + R_ground 1.0


def reactance_x(c_pf, f=F):
    return 1.0 / (2 * math.pi * f * c_pf * 1e-12)


def probe_loading(f=F):
    """How badly does a 16 pF probe load each node we might measure?"""
    rows = []
    # (a) at the antenna feed node: probe capacitance is in parallel with C_ant
    z_probe = 1.0 / (2 * math.pi * f * PROBE_PF * 1e-12)
    c_loaded = C_MODEL_PF + PROBE_PF
    f_shift = 1.0 / (2 * math.pi * math.sqrt(2.957e-6 * c_loaded * 1e-12))
    rows.append({
        "node": "antenna feed (high-Z)",
        "probe_impedance_ohm": z_probe,
        "antecedent_impedance_ohm": reactance_x(C_MODEL_PF),
        "distortion": f"adds {PROBE_PF:.0f} pF to a {C_MODEL_PF:.2f} pF antenna "
                      f"(+{100*PROBE_PF/C_MODEL_PF:.0f}%), resonance moves from "
                      f"{F/1e6:.1f} to {f_shift/1e6:.1f} MHz",
        "acceptable": False,
    })
    # (b) across the 10 ohm sense resistor
    z_par = 1.0 / (1.0 / R_SENSE + 1.0 / z_probe)
    rows.append({
        "node": "sense resistor (10 ohm)",
        "probe_impedance_ohm": z_probe,
        "antecedent_impedance_ohm": R_SENSE,
        "distortion": f"10 ohm || {z_probe:.0f} ohm = {z_par:.2f} ohm "
                      f"({100*(z_par/R_SENSE-1):+.1f}%)",
        "acceptable": True,
    })
    return rows


def l_from_two_caps(cf1_pf, cf2_pf, cs_pf, l_uh):
    """Forward: the two resonance frequencies the bench would see."""
    c1 = (cf1_pf + cs_pf) * 1e-12
    c2 = (cf2_pf + cs_pf) * 1e-12
    f1 = 1.0 / (2 * math.pi * math.sqrt(l_uh * 1e-6 * c1))
    f2 = 1.0 / (2 * math.pi * math.sqrt(l_uh * 1e-6 * c2))
    return f1, f2


def recover_l(f1, f2, cf1_pf, cf2_pf):
    w1, w2 = 2 * math.pi * f1, 2 * math.pi * f2
    return (1 / w1 ** 2 - 1 / w2 ** 2) / ((cf1_pf - cf2_pf) * 1e-12)


def stray_from(f, l_uh, cf_pf):
    return 1.0 / ((2 * math.pi * f) ** 2 * l_uh * 1e-6) * 1e12 - cf_pf


def l_error_budget(cf1_pf, cf2_pf, cs_pf, l_uh, tol_pf, df_over_f):
    """Perturb the inputs and see what L comes back as."""
    f1, f2 = l_from_two_caps(cf1_pf, cf2_pf, cs_pf, l_uh)
    f1 = f1 * (1 + df_over_f)
    f2 = f2 * (1 - df_over_f)
    got = recover_l(f1, f2, cf1_pf + tol_pf, cf2_pf - tol_pf)
    # frequency-only error (caps exact)
    got_f = recover_l(l_from_two_caps(cf1_pf, cf2_pf, cs_pf, l_uh)[0] * (1 + df_over_f),
                      l_from_two_caps(cf1_pf, cf2_pf, cs_pf, l_uh)[1] * (1 - df_over_f),
                      cf1_pf, cf2_pf)
    return {
        "true_L_uH": l_uh,
        "recovered_L_uH": got * 1e6,
        "total_error_pct": 100 * (got * 1e6 / l_uh - 1),
        "freq_only_error_pct": 100 * (got_f * 1e6 / l_uh - 1),
        "cap_only_error_pct": 100 * (got / got_f - 1),
        "cap_tolerance_used_pF": tol_pf,
        "freq_error_used_pct": df_over_f * 100,
    }


def bench_levels(v_emf_pp=4.0):
    """What the scope displays for a given generator EMF (High-Z display)."""
    v_emf_rms = v_emf_pp / (2 * math.sqrt(2))
    r_loop = R_GEN + R_SENSE + R_SIDE_MODEL
    i_rms = v_emf_rms / r_loop
    out = {
        "v_emf_pp": v_emf_pp,
        "loop_R_ohm": r_loop,
        "I_res_mA_rms": i_rms * 1e3,
        "V_sense_mV_rms": i_rms * R_SENSE * 1e3,
        "V_sense_mV_pp": i_rms * R_SENSE * 2 * math.sqrt(2) * 1e3,
        "V_across_L_V_rms": i_rms * reactance_x(C_MODEL_PF),
        "loaded_Q_at_resonance": reactance_x(C_MODEL_PF) / r_loop,
    }
    return out


def tuning_range():
    """What inductance range must the matching coil cover?"""
    rows = []
    for c in (6.0, 8.913, 12.0):
        x = reactance_x(c)
        l = x / (2 * math.pi * F)
        rows.append({"C_ant_pF": c, "X_ohm": -x, "L_required_uH": l * 1e6})
    return {
        "rows": rows,
        "L_min_uH": min(r["L_required_uH"] for r in rows),
        "L_max_uH": max(r["L_required_uH"] for r in rows),
        "conclusion": ("a fixed 2.96 uH coil is NOT usable: C_ant from 6 to 12 pF "
                       "needs about 2.2 to 4.4 uH. The coil must be tapped or "
                       "sliding-contact, not fixed, exactly as the sensitivity "
                       "analysis warned"),
    }


def c_sensitivity():
    """dC/C = -2 df/f - dL/L, applied to the real bench numbers."""
    df = 0.001     # DS2102E frequency measurement to 0.1%
    dl = 0.02      # L known to 2%
    dc = 2 * df + dl
    return {
        "dC_over_C_formula": "dC/C = -2*df/f - dL/L",
        "freq_accuracy_pct": df * 100,
        "L_accuracy_pct": dl * 100,
        "resulting_C_error_pct": dc * 100,
        "C_uncertainty_pF": C_MODEL_PF * dc,
        "note": ("frequency enters squared, so frequency accuracy is the dominant "
                 "single term; 0.1% frequency accuracy is easy with a scope "
                 "counter, and 2% on L is achievable only with the two-capacitor "
                 "method at a low test frequency"),
    }


def main():
    out = {"design_only": True, "not_a_measurement": True}

    out["probe_loading"] = probe_loading()
    out["tuning_range"] = tuning_range()
    out["bench_levels"] = bench_levels()
    out["c_sensitivity"] = c_sensitivity()

    # Two L-measurement scenarios, to show why a low test frequency is required.
    cs = 3.0                      # assumed stray/breadboard capacitance, pF
    l_true = 2.957                 # uH
    scen = []
    # (a) forced into the 28-34 MHz band: capacitance step is tiny
    f1, f2 = l_from_two_caps(6.8, 4.7, cs, l_true)
    scen.append({
        "scenario": "in-band (28-34 MHz), 6.8 / 4.7 pF",
        "f1_MHz": f1 / 1e6, "f2_MHz": f2 / 1e6,
        "C_step_pF": 6.8 - 4.7,
        "needs_generator_below_MHz": None,
        "error_budget": l_error_budget(6.8, 4.7, cs, l_true, tol_pf=0.25,
                                       df_over_f=0.001),
    })
    # (b) at a low frequency using a large known capacitor
    for cf_pair in ((100.0, 220.0),):
        f1, f2 = l_from_two_caps(cf_pair[0], cf_pair[1], cs, l_true)
        scen.append({
            "scenario": f"low frequency, {cf_pair[0]:.0f} / {cf_pair[1]:.0f} pF",
            "f1_MHz": f1 / 1e6, "f2_MHz": f2 / 1e6,
            "C_step_pF": cf_pair[1] - cf_pair[0],
            "needs_generator_below_MHz": math.ceil(max(f1, f2) / 1e6),
            "error_budget": l_error_budget(cf_pair[0], cf_pair[1], cs, l_true,
                                           tol_pf=0.25, df_over_f=0.001),
        })
    out["l_measurement_scenarios"] = scen

    # final combined C_ant uncertainty for the recommended route
    best = min(scen, key=lambda s: abs(s["error_budget"]["total_error_pct"]))
    out["recommended"] = {
        "scenario": best["scenario"],
        "L_error_pct": best["error_budget"]["total_error_pct"],
        "C_error_pct_combined": abs(best["error_budget"]["total_error_pct"])
                                + out["c_sensitivity"]["resulting_C_error_pct"],
        "note": ("measure L at the lowest frequency the generator reaches, using "
                 "a large accurately-known capacitance, then measure C_ant at "
                 "31 MHz against that L"),
    }

    out["prerequisites"] = {
        "blocking": [
            "signal generator model and its frequency range are still "
            "unconfirmed (S05-10 records only 'roughly covers 28-34 MHz'). The "
            "recommended route needs operation near 6-9 MHz, which is NOT "
            "established. If the generator cannot go below 28 MHz, fall back to "
            "the in-band route and accept very poor accuracy, or borrow an LCR "
            "meter",
            "probe model and its 10x tip capacitance are unconfirmed; the 16 pF "
            "figure used here is the DS2102E input specification, not the probe's",
            "whether a Low-Z / High-Z menu sets the source resistance or merely "
            "re-scales the displayed amplitude must be established by measuring "
            "the actual output into a known load, not by reading the menu",
        ],
        "non_blocking": [
            "the antenna must be built and mounted in its final position before "
            "measuring, and the mounting state recorded (height, ground plane, "
            "nearby metal, hand position), because impedance depends on all of them",
        ],
    }
    out["cannot_measure"] = [
        "radiation resistance separately from coil loss: the series-resonance "
        "method measures their SUM only. Splitting them needs an assumed coil Q, "
        "so the 28.5% efficiency figure stays an estimate, not a measurement",
        "the coil's own Q at 31 MHz (no Q meter available)",
        "directivity / ground-plane effectiveness, which is what actually decides "
        "the 6 m link",
        "far-field behaviour at 6 m, which is inside the near field "
        "(r/lambda = 0.62)",
    ]

    out["conclusion"] = {
        "is_the_measurement_worth_doing": (
            "yes, and it is the only way to settle the matching. The model's "
            "8.91 pF cannot be trusted to better than roughly a factor because "
            "the infinite-ground-plane assumption is wrong for a small chassis, "
            "and a +/-15% error in C_ant already cuts the antenna current to "
            "about a third"),
        "expected_accuracy": (
            f"C_ant to about +/-{out['recommended']['C_error_pct_combined']:.0f}% "
            "if L is measured at low frequency; the in-band-only route is much "
            "worse because the capacitance step is only about 2 pF"),
        "what_it_does_not_settle": (
            "even a perfect impedance measurement does not predict 6 m. It fixes "
            "the matching and the current; the link itself must be measured"),
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "measurement_design.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- stdout ----
    print("=== probe loading: why the antenna node must not be probed ===")
    for r in out["probe_loading"]:
        print(f"  {r['node']:26} Z_probe={r['probe_impedance_ohm']:6.0f} ohm  "
              f"vs {r['antecedent_impedance_ohm']:7.1f} ohm")
        print(f"  {'':26} {r['distortion']}  -> usable: {r['acceptable']}")
    print()
    print("=== what the scope should show (V_emf = 4 Vpp, High-Z display) ===")
    b = out["bench_levels"]
    print(f"  loop R at resonance   = {b['loop_R_ohm']:.1f} ohm")
    print(f"  I at resonance        = {b['I_res_mA_rms']:.1f} mA rms")
    print(f"  V across 10 ohm sense = {b['V_sense_mV_rms']:.0f} mV rms "
          f"= {b['V_sense_mV_pp']:.0f} mVpp   <- the resonance peak you look for")
    print(f"  V across L at res.    = {b['V_across_L_V_rms']:.1f} V rms  "
          f"(Q multiplication {b['loaded_Q_at_resonance']:.1f})")
    print()
    print("=== matching coil must be tunable ===")
    t = out["tuning_range"]
    for r in t["rows"]:
        print(f"  C_ant {r['C_ant_pF']:5.2f} pF -> X {r['X_ohm']:8.1f} ohm "
              f"-> L {r['L_required_uH']:.2f} uH")
    print(f"  required range: {t['L_min_uH']:.2f} - {t['L_max_uH']:.2f} uH")
    print()
    print("=== measuring L: two-capacitor method, two scenarios ===")
    for s in out["l_measurement_scenarios"]:
        eb = s["error_budget"]
        need = s["needs_generator_below_MHz"]
        print(f"  {s['scenario']}")
        print(f"     f = {s['f1_MHz']:.2f} / {s['f2_MHz']:.2f} MHz, "
              f"C step = {s['C_step_pF']:.1f} pF"
              + (f", needs generator below {need} MHz (UNCONFIRMED)" if need else ""))
        print(f"     L recovered {eb['recovered_L_uH']:.3f} uH vs "
              f"{eb['true_L_uH']:.3f} uH -> error {eb['total_error_pct']:+.1f}% "
              f"(freq part {eb['freq_only_error_pct']:+.1f}%, "
              f"cap part {eb['cap_only_error_pct']:+.1f}%)")
    print()
    print("=== blocking prerequisites (must be settled before the bench step) ===")
    for p in out["prerequisites"]["blocking"]:
        print(f"  - {p[:110]}")
        print(f"    {'':110}"[:0])
    print()
    print("=== C_ant sensitivity ===")
    c = out["c_sensitivity"]
    print(f"  {c['dC_over_C_formula']}")
    print(f"  with df/f = {c['freq_accuracy_pct']:.1f}% and dL/L = "
          f"{c['L_accuracy_pct']:.1f}% -> dC/C = {c['resulting_C_error_pct']:.1f}% "
          f"= {c['C_uncertainty_pF']:.2f} pF")
    print()
    print(f"recommended route: {out['recommended']['scenario']}")
    print(f"  combined C_ant uncertainty about "
          f"+/-{out['recommended']['C_error_pct_combined']:.0f}%")
    print()
    print("written:", RESULTS / "measurement_design.json")


if __name__ == "__main__":
    main()
