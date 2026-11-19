"""P2 bench calculator: turn DS2102E + generator readings into C_ant and R_total
with a defensible +-3% uncertainty budget.

This is NOT a simulation and NOT a measurement. It is the arithmetic layer of
the measurement procedure in P2_天线阻抗实测规程.md: you type in the numbers the
scope shows, it returns C_ant, R_total, the propagated uncertainty, and a clear
PASS / FAIL against the +-3% target.

Why a program and not a spreadsheet: the two-capacitor and the resonance-point
relations are easy to get subtly wrong (see the three traps documented below),
and an auditable, version-controlled formula is worth more than a cell formula
nobody can review.

    py -3 p2_antenna_calculator.py --demo
    py -3 p2_antenna_calculator.py --from-json my_reading.json

Three traps this file is built to avoid
---------------------------------------
1. **Probe on the antenna node.** A 16 pF probe across an 8.91 pF antenna adds
   +180% and drags resonance from 31.0 MHz to 18.5 MHz. Always sense across the
   10 ohm resistor and use CH1-CH2.
2. **Peak vs RMS confusion.** The generator's front panel may show Vpp into
   50 ohm while the actual source resistance is still 50 ohm and the open-circuit
   EMF is twice what the panel says when lightly loaded. Everything here takes
   explicit units and converts once, at the boundary.
3. **Ignoring the source resistance.** The loop total R includes R_gen (50 ohm),
   R_sense (10 ohm) and the antenna+coil loss. Omitting R_gen makes R_total look
   ~2x too small and Q ~2x too large.

Uncertainty model
-----------------
    C_total = 1 / ((2*pi*f_res)^2 * L)
    dC/C = -2*df/f - dL/L                    (frequency enters squared)
    R = V_emf / I - R_gen - R_sense,  I = V_sense / R_sense

The +-3% target applies to C_ant (the quantity that sets the tuning inductance).
R_total is reported with its own uncertainty and no pass/fail, because the
series-resonance method measures R_total (radiation + coil + ground) as a sum
and cannot separate the radiation resistance from the loss.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict, field

# ---------------------------------------------------------------------------
# Physical constants and bench assumptions (all overridable from the CLI)
# ---------------------------------------------------------------------------
R_GEN_DEFAULT = 50.0      # ohm, function-generator source resistance
R_SENSE = 10.0            # ohm, current-sense resistor in the loop
TARGET_TOL_PCT = 3.0      # the P2 acceptance target on C_ant


# ---------------------------------------------------------------------------
# Core relations
# ---------------------------------------------------------------------------
def c_total_from_resonance(f_res_hz: float, L_h: float) -> float:
    """Total series capacitance at resonance: C = 1/((2*pi*f)^2 * L)."""
    if f_res_hz <= 0 or L_h <= 0:
        raise ValueError("f_res and L must be positive")
    return 1.0 / ((2 * math.pi * f_res_hz) ** 2 * L_h)


def inductance_two_capacitor(f1_hz: float, c1_f: float,
                             f2_hz: float, c2_f: float) -> float:
    """L from two resonances with different known capacitors.

    Eliminates the unknown stray capacitance C_s:
        1/(w1^2 L) = C1 + C_s
        1/(w2^2 L) = C2 + C_s
    =>  L = (1/w1^2 - 1/w2^2) / (C1 - C2)

    Both capacitors must be at the SAME coil position and same fixture, and the
    frequency step should be large (100 pF vs 220 pF is the recommended pair).
    Using two nearby in-band capacitors (e.g. 4.7 and 6.8 pF) gives a -20% error
    because the capacitance difference is comparable to the capacitor tolerance.
    """
    if abs(c1_f - c2_f) < 1e-15:
        raise ValueError("the two capacitors must differ")
    if f1_hz <= 0 or f2_hz <= 0:
        raise ValueError("frequencies must be positive")
    a1 = 1.0 / (2 * math.pi * f1_hz) ** 2
    a2 = 1.0 / (2 * math.pi * f2_hz) ** 2
    return (a1 - a2) / (c1_f - c2_f)


def stray_capacitance(f1_hz: float, c1_f: float, L_h: float) -> float:
    """Fixture stray capacitance implied by a two-capacitor solution."""
    return c_total_from_resonance(f1_hz, L_h) - c1_f


def sense_current_a(v_sense_v: float, r_sense: float = R_SENSE) -> float:
    """Loop current from the voltage across the sense resistor."""
    return v_sense_v / r_sense


def loop_resistance_ohm(v_emf_v: float, i_a: float,
                        r_gen: float = R_GEN_DEFAULT,
                        r_sense: float = R_SENSE) -> float:
    """R_total = V_emf/I - R_gen - R_sense.

    V_emf is the generator's OPEN-CIRCUIT EMF at the drive level used. If the
    generator panel is set to show the voltage into 50 ohm, the EMF is that
    displayed value (the panel already accounts for its own 50 ohm); if it shows
    the open-circuit voltage into high-Z, the EMF is that value. Never mix the
    two conventions inside one calculation.
    """
    if i_a <= 0:
        raise ValueError("current must be positive")
    return v_emf_v / i_a - r_gen - r_sense


# ---------------------------------------------------------------------------
# Uncertainty propagation
# ---------------------------------------------------------------------------
def c_uncertainty_pct(df_over_f_pct: float, dL_over_L_pct: float) -> float:
    """dC/C = -2*df/f - dL/L, combined in quadrature (independent errors)."""
    return math.hypot(2.0 * df_over_f_pct, dL_over_L_pct)


def c_uncertainty_linear_pct(df_over_f_pct: float, dL_over_L_pct: float) -> float:
    """Worst-case linear sum, for when the errors are not independent."""
    return 2.0 * abs(df_over_f_pct) + abs(dL_over_L_pct)


@dataclass
class CoilCalibration:
    """One coil position calibrated by the two-capacitor method.

    Capacitor tolerance is specified in ABSOLUTE pF, not percent, because that is
    how small RF capacitors are actually sold and how the stage's own budget was
    built ("±0.25 pF"). This matters enormously:

        100 pF / 220 pF, tol 0.25 pF -> dL/L ~ 0.3%   (the recommended pair)
          4.7 pF / 6.8 pF, tol 0.25 pF -> dL/L ~ 17%  (unusable)

    The second case is not a hypothetical: it is why the in-band measurement route
    was rejected in 02_AM-ALT.3_勘误 section 7.2. Modelling tolerance as a percent
    hides the effect completely, because the percent error is the same for both
    pairs while the absolute error is what enters L = (A1-A2)/(C1-C2).
    """
    position: str
    c1_pF: float
    c2_pF: float
    f1_Hz: float
    f2_Hz: float
    capacitor_tol_pF: float = 0.25      # absolute, per capacitor
    frequency_tol_pct: float = 0.1      # scope counter accuracy
    L_uH: float = field(init=False)
    C_stray_pF: float = field(init=False)
    L_tol_pct: float = field(init=False)

    def __post_init__(self):
        self.L_uH = inductance_two_capacitor(
            self.f1_Hz, self.c1_pF * 1e-12,
            self.f2_Hz, self.c2_pF * 1e-12) * 1e6
        self.C_stray_pF = stray_capacitance(
            self.f1_Hz, self.c1_pF * 1e-12, self.L_uH * 1e-6) * 1e12
        # L = (A1-A2)/(C1-C2); the difference carries sqrt(2) x the per-cap tolerance
        d_cap_pct = math.sqrt(2.0) * self.capacitor_tol_pF / abs(self.c1_pF - self.c2_pF) * 100
        self.L_tol_pct = math.hypot(d_cap_pct, 2 * self.frequency_tol_pct)


@dataclass
class AntennaReading:
    """One antenna resonance reading at a fixed coil position."""
    position: str
    f_res_Hz: float
    v_sense_V: float
    v_emf_V: float
    L_uH: float
    L_tol_pct: float
    C_stray_pF: float
    frequency_tol_pct: float = 0.1
    r_gen: float = R_GEN_DEFAULT
    r_sense: float = R_SENSE
    differential_residual_V: float | None = None
    C_ant_pF: float = field(init=False)
    C_ant_tol_pct: float = field(init=False)
    R_total_ohm: float = field(init=False)
    Q_loaded: float = field(init=False)
    bandwidth_kHz: float = field(init=False)

    def __post_init__(self):
        c_tot = c_total_from_resonance(self.f_res_Hz, self.L_uH * 1e-6)
        self.C_ant_pF = c_tot * 1e12 - self.C_stray_pF
        self.C_ant_tol_pct = c_uncertainty_pct(self.frequency_tol_pct, self.L_tol_pct)
        i = sense_current_a(self.v_sense_V, self.r_sense)
        self.R_total_ohm = loop_resistance_ohm(self.v_emf_V, i, self.r_gen, self.r_sense)
        xl = 2 * math.pi * self.f_res_Hz * self.L_uH * 1e-6
        self.Q_loaded = xl / self.R_total_ohm if self.R_total_ohm > 0 else float("nan")
        self.bandwidth_kHz = (self.f_res_Hz / self.Q_loaded) / 1e3 if self.Q_loaded else float("nan")


def evaluate(cal: CoilCalibration, reading: AntennaReading) -> dict:
    """Turn one calibration + one reading into a verdict."""
    c_lin = c_uncertainty_linear_pct(reading.frequency_tol_pct, reading.L_tol_pct)
    c_quad = reading.C_ant_tol_pct
    meets_quad = c_quad <= TARGET_TOL_PCT
    meets_lin = c_lin <= TARGET_TOL_PCT

    verdict = "PASS" if meets_quad else ("PASS_ONLY_QUADRATURE" if meets_lin else "FAIL")
    return {
        "coil_position": reading.position,
        "L_uH": round(cal.L_uH, 4),
        "L_tol_pct": round(cal.L_tol_pct, 2),
        "C_stray_pF": round(cal.C_stray_pF, 3),
        "f_res_Hz": reading.f_res_Hz,
        "C_ant_pF": round(reading.C_ant_pF, 4),
        "C_ant_tol_pct_quadrature": round(c_quad, 2),
        "C_ant_tol_pct_linear": round(c_lin, 2),
        "target_pct": TARGET_TOL_PCT,
        "verdict": verdict,
        "R_total_ohm": round(reading.R_total_ohm, 3),
        "Q_loaded": round(reading.Q_loaded, 2),
        "bandwidth_kHz": round(reading.bandwidth_kHz, 1),
        "L_required_for_31MHz_uH": round(
            1.0 / ((2 * math.pi * 31e6) ** 2 * reading.C_ant_pF * 1e-12) * 1e6, 4),
        "differential_residual_V": reading.differential_residual_V,
        "notes": _notes(reading, meets_quad, meets_lin),
    }


def _notes(r: AntennaReading, ok_quad: bool, ok_lin: bool) -> list[str]:
    out = []
    if r.differential_residual_V is not None:
        frac = r.differential_residual_V / r.v_sense_V if r.v_sense_V else float("inf")
        if frac > 0.05:
            out.append(
                f"CH1-CH2 residual is {frac * 100:.1f}% of the sense voltage; "
                "above 5% the differential subtraction is not trustworthy, re-null the probes")
    if not ok_quad and ok_lin:
        out.append("meets +-3% only under the linear (worst-case) sum; report both figures")
    if not ok_quad and not ok_lin:
        out.append(
            "does not reach +-3%: the dominant term is the coil inductance. "
            "Recalibrate L with a larger capacitor step (100/220 pF) at a low frequency")
    if r.C_ant_pF <= 0:
        out.append("C_ant came out non-physical (<= 0): check the stray capacitance and L")
    return out


# ---------------------------------------------------------------------------
# Demo / self-test with the model values from the stage
# ---------------------------------------------------------------------------
def demo() -> int:
    print("=" * 78)
    print("P2 calculator self-test, using the AM-ALT.3 design values")
    print("=" * 78)
    print()

    # The stage's own expected bench numbers (results/measurement_design.json).
    # V_emf there is 4.0 Vpp, i.e. 1.4142 V rms -- a trap worth showing, since
    # feeding Vpp straight into an RMS relation overstates the current by sqrt2.
    print("-- expected bench levels (from measurement_design.json) --")
    v_emf_pp = 4.0
    v_emf = v_emf_pp / (2 * 2 ** 0.5)
    loop_r = 73.824
    i = v_emf / loop_r
    v_sense = i * R_SENSE
    print(f"   V_emf = {v_emf_pp} Vpp = {v_emf:.4f} V rms")
    print(f"   loop R = {loop_r:.3f} ohm -> I = {i * 1e3:.3f} mA rms")
    print(f"   V across 10 ohm = {v_sense * 1e3:.2f} mV rms = {v_sense * 2 * 2 ** 0.5 * 1e3:.1f} mVpp")
    check = abs(v_sense * 1e3 - 191.56555623822808) < 0.01
    print(f"   matches the recorded 191.57 mV rms: {check}")
    if not check:
        print("   !! the Vpp-to-rms conversion is wrong; stops here")
        return 1
    print()

    # Two-capacitor calibration at a low frequency, as the procedure prescribes
    print("-- coil calibration, 100 pF / 220 pF at low frequency --")
    # solve the forward problem for a 2.9572 uH coil with 3 pF stray
    L_true = 2.9572e-6
    c_stray = 3.0e-12
    f1 = 1 / (2 * math.pi * math.sqrt(L_true * (100e-12 + c_stray)))
    f2 = 1 / (2 * math.pi * math.sqrt(L_true * (220e-12 + c_stray)))
    print(f"   synthetic f1 = {f1 / 1e6:.4f} MHz, f2 = {f2 / 1e6:.4f} MHz")
    cal = CoilCalibration("nominal", 100.0, 220.0, f1, f2)
    print(f"   recovered L = {cal.L_uH:.4f} uH (true 2.9572), "
          f"stray = {cal.C_stray_pF:.3f} pF (true 3.0), L tol = +-{cal.L_tol_pct:.2f}%")
    recovered_ok = abs(cal.L_uH - 2.9572) < 0.01 and abs(cal.C_stray_pF - 3.0) < 0.1
    print(f"   round-trip correct: {recovered_ok}")
    print()

    # Then the antenna reading. Truth: C_ant = 8.913 pF, stray = 3 pF, L = 2.9572 uH.
    # Note the resonance is NOT at 31 MHz: with stray present C_total = 11.913 pF,
    # so the SAME coil resonates low. This is the physically correct behaviour and
    # is exactly why the stray capacitance must be measured and subtracted before
    # choosing the tuning inductance -- the design's "2.9572 uH gives 31 MHz" only
    # holds when C_total = 8.913 pF, i.e. when there is no stray at all.
    print("-- antenna reading (truth: C_ant 8.913 pF, stray 3 pF, L 2.9572 uH) --")
    f_res = 1 / (2 * math.pi * math.sqrt(L_true * (8.913e-12 + c_stray)))
    f_if_no_stray = 1 / (2 * math.pi * math.sqrt(L_true * 8.913e-12))
    print(f"   f_res with 3 pF stray = {f_res / 1e6:.4f} MHz")
    print(f"   f_res with 0 pF stray = {f_if_no_stray / 1e6:.4f} MHz  (the design point)")
    # pick the EMF that gives R_total = 14.824 ohm
    r_target = 14.824
    i_need = 4.0 / (r_target + R_GEN_DEFAULT + R_SENSE)
    reading = AntennaReading(
        position="nominal", f_res_Hz=f_res, v_sense_V=i_need * R_SENSE,
        v_emf_V=4.0, L_uH=cal.L_uH, L_tol_pct=cal.L_tol_pct,
        C_stray_pF=cal.C_stray_pF, differential_residual_V=0.002)
    out = evaluate(cal, reading)
    for k, v in out.items():
        if k == "notes":
            for n in v:
                print(f"   note: {n}")
        else:
            print(f"   {k:32} {v}")

    ok = (abs(out["C_ant_pF"] - 8.913) < 0.05
          and abs(out["R_total_ohm"] - r_target) < 0.1
          and out["verdict"].startswith("PASS"))
    print()
    print(f"   C_ant recovered despite the detuned resonance: {ok}")
    print("   -> the coil L is fixed by calibration, so C_total comes straight from")
    print("      f_res; subtracting the measured stray gives C_ant regardless of")
    print("      whether the reading happens to land near 31 MHz.")
    print()

    # Show why the in-band capacitor pair is rejected
    print("-- why 100/220 pF and not 4.7/6.8 pF (absolute, not percent, tolerance) --")
    f1b = 1 / (2 * math.pi * math.sqrt(L_true * (4.7e-12 + c_stray)))
    f2b = 1 / (2 * math.pi * math.sqrt(L_true * (6.8e-12 + c_stray)))
    cal_bad = CoilCalibration("in-band", 4.7, 6.8, f1b, f2b, capacitor_tol_pF=0.25)
    err = (cal_bad.L_uH - 2.9572) / 2.9572 * 100
    print(f"   4.7/6.8 pF pair, +-0.25 pF: L = {cal_bad.L_uH:.4f} uH, error {err:+.1f}%, "
          f"tolerance +-{cal_bad.L_tol_pct:.1f}%")
    print(f"   100/220 pF pair, +-0.25 pF: L = {cal.L_uH:.4f} uH, error "
          f"{(cal.L_uH - 2.9572) / 2.9572 * 100:+.2f}%, tolerance +-{cal.L_tol_pct:.2f}%")
    bad_is_worse = cal_bad.L_tol_pct > 10 * cal.L_tol_pct
    print(f"   in-band pair is >10x worse: {bad_is_worse}")
    print()

    print("=" * 78)
    return 0 if (check and recovered_ok and ok and bad_is_worse) else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", action="store_true",
                    help="run the self-test with the design values")
    ap.add_argument("--from-json", metavar="PATH",
                    help="evaluate a reading file (see P2_天线阻抗实测规程.md for the schema)")
    args = ap.parse_args(argv)

    if args.demo:
        return demo()

    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        cal = CoilCalibration(**data["coil_calibration"])
        reading = AntennaReading(
            position=data["antenna_reading"]["position"],
            f_res_Hz=data["antenna_reading"]["f_res_Hz"],
            v_sense_V=data["antenna_reading"]["v_sense_V"],
            v_emf_V=data["antenna_reading"]["v_emf_V"],
            L_uH=cal.L_uH, L_tol_pct=cal.L_tol_pct, C_stray_pF=cal.C_stray_pF,
            differential_residual_V=data["antenna_reading"].get("differential_residual_V"))
        out = evaluate(cal, reading)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if out["verdict"].startswith("PASS") else 2

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
