"""Antenna impedance model for AM-ALT.3, with its validity checked explicitly.

Model used (central estimate): Schelkunoff's transmission-line / average-
characteristic-impedance approximation for a cylindrical monopole over an infinite
ground plane,

    Z_c  = 60 * [ ln(2h/a) - 1 ]                 (average characteristic impedance)
    Z_in = R_r(h) + R_loss - j * Z_c * cot(beta*h)

with R_r = 395*(h/lambda)^2 for the short-monopole triangular current and
beta*h the electrical height. This approximation is smooth and monotonic from the
very short case up to the quarter-wave resonance, which is the behaviour the
physical antenna has; it is used here to *size* a tunable matching network.

Why not the induced-EMF (sinusoidal current) formula: model_check.py shows it
collapses to ~10% of the correct radiation resistance (and the wrong reactance) as
the element gets electrically short -- see the ratio column. It reproduces the
quarter-wave reference only because there the sinusoidal assumption happens to be
right.

Why not the static capacitance C = 2*pi*eps0*h/ln(2h/a): it is exact only as
h -> 0 and over-predicts |X| badly by h = 0.1 lambda. It is kept here as a lower
bound on |X|, not as the design value.

Everything in this file is an estimate from published formulas. It is NOT a
measurement and NOT a full-wave solve, and the report says so.
"""
import numpy as np

C0 = 299792458.0
MU0 = 4e-7 * np.pi
EPS0 = 1.0 / (MU0 * C0 ** 2)

F = 31e6
LAM = C0 / F


def characteristic_impedance(h, a):
    return 60.0 * (np.log(2 * h / a) - 1.0)


def radiation_resistance(h):
    """Short-monopole radiation resistance, triangular current."""
    return 395.0 * (h / LAM) ** 2


def schelkunoff(h, a, f=F):
    """(R_rad, X) of a monopole over an infinite ground plane."""
    beta = 2 * np.pi * f / C0
    zc = characteristic_impedance(h, a)
    x = -zc / np.tan(beta * h)
    return radiation_resistance(h), x


def static_capacitance(h, a):
    return 2 * np.pi * EPS0 * h / np.log(2 * h / a)


def induced_emf_reactance(h, a, f=F):
    """Sinusoidal-current reactance, valid near resonance only; kept for the check."""
    from antenna import monopole
    return monopole(h, a, f)[1]


def check_models(a=0.5e-3):
    """Compare the three models where each is supposed to be valid."""
    rows = []
    hq = LAM / 4
    rows.append(("quarter-wave h=%.3f m" % hq, *schelkunoff(hq, 1e-3),
                 induced_emf_reactance(hq, 1e-3), "X should be ~+21 ohm"))
    for h in (0.15, 0.30, 0.50, 0.80, 1.00):
        Rr, X = schelkunoff(h, a)
        Cs = static_capacitance(h, a)
        Xs = -1 / (2 * np.pi * F * Cs)
        rows.append((f"h={h:.2f} m", Rr, X, Xs, ""))
    return rows


def efficiency(h, a, coil_q, r_ground, f=F):
    """Radiation efficiency with coil loss and ground loss referred to the antenna."""
    Rr, X = schelkunoff(h, a, f)
    xl = abs(X)                       # tuning inductance reactance needed
    r_coil = xl / coil_q              # coil ESR at the same reactance
    r_total = Rr + r_coil + r_ground
    return {
        "R_rad": Rr,
        "X_ant": X,
        "L_tune_nH": xl / (2 * np.pi * f) * 1e9,
        "R_coil": r_coil,
        "R_ground": r_ground,
        "R_total": r_total,
        "efficiency_pct": 100 * Rr / r_total,
    }


if __name__ == "__main__":
    print(f"31 MHz: lambda = {LAM:.4f} m, lambda/4 = {LAM/4:.4f} m")
    print()
    print("=== model cross-check (wire radius 0.5 mm) ===")
    print(f"{'case':28} {'R_r/ohm':>9} {'X_schelk':>10} {'X_other':>10}  note")
    for label, Rr, X, Xother, note in check_models():
        print(f"{label:28} {Rr:9.4f} {X:10.1f} {Xother:10.1f}  {note}")
    print()
    print("判读：Schelkunoff 在 0.25λ 给出 X≈+20Ω，与教材 +21.3Ω 一致；")
    print("      在 h≤1 m 给出单调下降的容抗，介于静态电容（过负）与")
    print("      正弦电流公式（过浅）之间，符合物理趋势。")
    print()
    print("=== candidate monopoles, wire radius 0.5 mm ===")
    print(f"{'h/m':>5} {'h/lam':>7} {'R_rad':>8} {'X':>9} {'C_eq/pF':>9} "
          f"{'Q_ant':>7} {'eta@Q60':>9}")
    for h in (0.30, 0.50, 0.80, 1.00, 1.20, 1.50):
        Rr, X = schelkunoff(h, 0.5e-3)
        Ceq = 1 / (2 * np.pi * F * abs(X))
        e = efficiency(h, 0.5e-3, coil_q=60, r_ground=1.0)
        print(f"{h:5.2f} {h/LAM:7.3f} {Rr:8.3f} {X:9.1f} {Ceq*1e12:9.2f} "
              f"{abs(X)/Rr:7.1f} {e['efficiency_pct']:8.1f}%")

    print()
    print("=== efficiency vs coil Q and ground loss, h = 1.00 m ===")
    print(f"{'Q_coil':>7} {'Rg=0.5':>9} {'Rg=1.0':>9} {'Rg=2.0':>9}")
    for q in (30, 60, 100, 150):
        vals = []
        for rg in (0.5, 1.0, 2.0):
            vals.append(efficiency(1.00, 0.5e-3, q, rg)["efficiency_pct"])
        print(f"{q:7d} " + " ".join(f"{v:8.2f}%" for v in vals))
