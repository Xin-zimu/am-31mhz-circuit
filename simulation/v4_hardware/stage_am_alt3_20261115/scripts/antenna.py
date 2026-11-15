"""Antenna impedance estimates for the AM-ALT.3 candidates at 31 MHz.

All results come from the induced-EMF method with an assumed sinusoidal current
distribution (Balanis, Antenna Theory, ch. 4), plus the standard short-monopole
capacitance formula as an independent check of the reactance.

This is an *engineering estimate from published formulas*, not a full-wave solve
and not a measurement. `validate()` reproduces the two textbook reference
impedances before the short-antenna numbers are used.

The aim is to bound the design: the real antenna's impedance will also depend on
the counterpoise/ground plane, the wire routing, nearby metal and the hand, so
the final matching network must be adjustable and measured.
"""
import numpy as np
from scipy.special import sici  # noqa: F401  (fallback implemented below)

C0 = 299792458.0
MU0 = 4e-7 * np.pi
EPS0 = 1.0 / (MU0 * C0 ** 2)
ETA0 = np.sqrt(MU0 / EPS0)
EULER = 0.5772156649015329

try:
    from scipy.special import sici as _sici  # type: ignore

    def Si(x):
        return float(_sici(x)[0])

    def Ci(x):
        return float(_sici(x)[1])
except Exception:  # pure-python fallback, adequate for 0 < x < 60
    def Si(x, n=4000):
        t = np.linspace(0, x, n)
        y = np.where(t == 0, 1.0, np.sin(t) / np.where(t == 0, 1, t))
        return float(np.trapezoid(y, t))

    def Ci(x, n=4000):
        t = np.linspace(1e-9, x, n)
        return float(EULER + np.log(x) + np.trapezoid((np.cos(t) - 1) / t, t))


def induced_emf_dipole(length, radius, freq):
    """Centre-fed straight dipole, sinusoidal current: (Rr, Xr) in ohm."""
    lam = C0 / freq
    k = 2 * np.pi / lam
    kl = k * length
    Rr = (ETA0 / (2 * np.pi)) * (
        EULER + np.log(kl) - Ci(kl)
        + 0.5 * np.sin(kl) * (Si(2 * kl) - 2 * Si(kl))
        + 0.5 * np.cos(kl) * (EULER + np.log(kl / 2) + Ci(2 * kl) - 2 * Ci(kl))
    )
    Xr = (ETA0 / (4 * np.pi)) * (
        2 * Si(kl)
        + np.cos(kl) * (2 * Si(kl) - Si(2 * kl))
        - np.sin(kl) * (2 * Ci(kl) - Ci(2 * kl) - Ci(2 * k * radius ** 2 / length))
    )
    return Rr, Xr


def monopole(height, radius, freq):
    """Monopole over an infinite perfect ground: half of a 2h dipole."""
    Rr, Xr = induced_emf_dipole(2 * height, radius, freq)
    return Rr / 2.0, Xr / 2.0


def short_monopole_capacitance(height, radius):
    """C = 2*pi*eps0*h / ln(2h/a); valid for h >> a."""
    return 2 * np.pi * EPS0 * height / np.log(2 * height / radius)


def small_loop(radius_loop, wire_radius, freq, turns=1):
    """Radiation resistance and inductance of a small circular loop."""
    lam = C0 / freq
    area = np.pi * radius_loop ** 2
    Rr = 31171.0 * turns ** 2 * (area / lam ** 2) ** 2
    # Wheeler / standard small-loop inductance
    L = MU0 * radius_loop * turns ** 2 * (np.log(8 * radius_loop / wire_radius) - 2)
    return Rr, L


def validate(freq=31e6):
    """Reproduce the textbook references before trusting the short cases."""
    lam = C0 / freq
    rd, xd = induced_emf_dipole(lam / 2, 1e-3, freq)
    rm, xm = monopole(lam / 4, 1e-3, freq)
    return [
        ("半波振子 0.5λ", rd, xd, "73.1 + j42.5"),
        ("四分之一波长单极子", rm, xm, "36.5 + j21.3"),
    ]


CASES = [
    ("单极子 h=1.00m  (0.103λ)", 1.00),
    ("单极子 h=0.80m  (0.083λ)", 0.80),
    ("单极子 h=0.50m  (0.052λ)", 0.50),
    ("单极子 h=0.30m  (0.031λ)", 0.30),
    ("偶极子 0.5+0.5m (0.103λ)", None),
]

if __name__ == "__main__":
    f = 31e6
    lam = C0 / f
    print(f"31 MHz: lambda = {lam:.3f} m, lambda/4 = {lam/4:.3f} m")
    print()
    print("=== 求解器校验（用教材参考值核对公式实现） ===")
    for label, R, X, ref in validate(f):
        print(f"{label:22} {R:7.2f} {X:+8.2f} j ohm   参考 {ref}")

    print()
    print("=== 候选天线（导线半径 0.5 mm） ===")
    for label, h in CASES:
        if h is None:
            R, X = induced_emf_dipole(1.0, 0.5e-3, f)
            kind = "dipole"
        else:
            R, X = monopole(h, 0.5e-3, f)
            kind = "monopole"
        Q = abs(X) / R
        print(f"{label:26} R={R:8.3f} ohm  X={X:+9.1f} ohm  |Z|={np.hypot(R,X):8.1f}  "
              f"Q_ant={Q:6.1f}")

    print()
    print("=== 电抗的独立核对：短单极子电容公式 ===")
    for h in (1.00, 0.80, 0.50, 0.30):
        C = short_monopole_capacitance(h, 0.5e-3)
        Xc = -1 / (2 * np.pi * f * C)
        _, Xe = monopole(h, 0.5e-3, f)
        print(f"h={h:.2f}m  C={C*1e12:5.2f} pF  X_C={Xc:9.1f} ohm  X_emf={Xe:9.1f} ohm  "
              f"差 {100*(Xe/Xc-1):+6.1f}%")

    print()
    print("=== 小环天线（1m 周长，导线 1mm） ===")
    Rr, L = small_loop(1 / (2 * np.pi), 0.5e-3, f)
    XL = 2 * np.pi * f * L
    print(f"环半径 {1/(2*np.pi)*100:.1f} cm  Rr={Rr*1e3:.2f} mOhm  L={L*1e6:.2f} uH  "
          f"XL={XL:.1f} ohm")
    print("→ 辐射电阻比短单极子低约 "
          f"{monopole(1.0, .5e-3, f)[0]/Rr:.0f} 倍，在 13 mA 级电流下不实用")
