"""Sanity-check the special-function implementations before trusting any result."""
import numpy as np

try:
    from scipy.special import sici

    def Si(x):
        return float(sici(x)[0])

    def Ci(x):
        return float(sici(x)[1])

    HAVE = "scipy"
except Exception:
    EULER = 0.5772156649015329

    def Si(x, n=200001):
        t = np.linspace(0.0, x, n)
        y = np.ones_like(t)
        nz = t != 0
        y[nz] = np.sin(t[nz]) / t[nz]
        return float(np.trapezoid(y, t))

    def Ci(x, n=200001):
        t = np.linspace(1e-12, x, n)
        return float(EULER + np.log(x) + np.trapezoid((np.cos(t) - 1) / t, t))

    HAVE = "numpy"

KNOWN = [(0.5, 0.493107418), (1.0, 0.946083070), (2.0, 1.605412977),
         (5.0, 1.549931245), (10.0, 1.658347594)]
KNOWN_CI = [(0.5, -0.177784078), (1.0, 0.337403923), (2.0, 0.422980829),
            (5.0, -0.190029750), (10.0, -0.045456433)]

print("implementation:", HAVE)
print("Si:")
for x, ref in KNOWN:
    v = Si(x)
    print(f"  Si({x:5.2f}) = {v:12.9f}   ref {ref:12.9f}   err {v-ref:+.2e}")
print("Ci:")
for x, ref in KNOWN_CI:
    v = Ci(x)
    print(f"  Ci({x:5.2f}) = {v:12.9f}   ref {ref:12.9f}   err {v-ref:+.2e}")
