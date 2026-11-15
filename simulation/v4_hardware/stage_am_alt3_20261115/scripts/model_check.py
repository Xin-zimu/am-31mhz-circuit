"""Decide which antenna model to trust, by testing each in the limit where the
answer is known analytically.

Two candidate models:
  A. induced-EMF with sinusoidal current (Balanis 4-93). Reproduces the half-wave
     and quarter-wave references exactly, but its current assumption is wrong for
     electrically short elements -- the regime this project needs.
  B. short-monopole radiation resistance R_r = 395 (h/lambda)^2 and the static
     capacitance C = 2*pi*eps0*h/ln(2h/a). Valid only for h << lambda.

The test: as L -> 0, model A must approach R_r = 197 (L/lambda)^2 for a dipole.
If it does, A is trustworthy in the short limit and should be preferred; if it
does not, A must not be used for the 1 m antenna and the short-antenna formulas
(bounded from both sides) are the honest choice.
"""
import numpy as np
from antenna import induced_emf_dipole, C0, EPS0

f = 31e6
lam = C0 / f
a = 0.5e-3

print(f"lambda = {lam:.4f} m at 31 MHz, wire radius {a*1e3:.1f} mm")
print()
print("Test A in the short-dipole limit:  R_emf  vs  197*(L/lambda)^2")
print(f"{'L/lambda':>9} {'R_emf':>12} {'R_short':>12} {'ratio':>8} {'X_emf':>12}")
for frac in (0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.25):
    L = frac * lam
    R, X = induced_emf_dipole(L, a, f)
    R_short = 197.0 * (L / lam) ** 2
    print(f"{frac:9.3f} {R:12.6f} {R_short:12.6f} {R/R_short:8.3f} {X:12.2f}")

print()
print("Test B: static capacitance model, C = 2*pi*eps0*h/ln(2h/a)")
print(f"{'h/m':>6} {'h/lam':>7} {'C/pF':>8} {'X_C/ohm':>11} {'R_r=395(h/lam)^2':>18}")
for h in (0.3, 0.5, 0.8, 1.0):
    C = 2 * np.pi * EPS0 * h / np.log(2 * h / a)
    Xc = -1 / (2 * np.pi * f * C)
    Rr = 395.0 * (h / lam) ** 2
    print(f"{h:6.2f} {h/lam:7.3f} {C*1e12:8.2f} {Xc:11.1f} {Rr:18.3f}")

print()
print("Test A at the same heights (monopole = half of a 2h dipole):")
for h in (0.3, 0.5, 0.8, 1.0):
    R, X = induced_emf_dipole(2 * h, a, f)
    print(f"  h={h:.2f} m:  R={R/2:8.3f} ohm   X={X/2:+9.1f} ohm")
