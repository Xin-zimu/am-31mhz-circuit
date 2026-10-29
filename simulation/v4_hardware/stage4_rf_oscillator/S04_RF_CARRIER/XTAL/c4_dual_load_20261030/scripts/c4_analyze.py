# -*- coding: utf-8 -*-
"""C4 analysis: dual-load amplitude convergence.

The question is narrow and must be answered without help from the frequency
correction: does the 10 kOhm load stay under 2.1 Vpp once the step is fine
enough that trap has converged?

Convergence is judged only from the amplitude series itself:
  * adjacent differences must shrink
  * an order-p extrapolation is reported but flagged as conditional
  * the two loads must be compared at IDENTICAL numerical settings
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c4env          # noqa: F401
import c3lib as L

LOAD = {"2k": "2 kΩ", "10k": "10 kΩ"}


def rows():
    p = os.path.join(L.RESDIR, "c4_dual.json")
    return L.json_load(p) if os.path.exists(p) else []


def key(r):
    return (r.get("method"), r.get("reltol"), r.get("rload"), float(r.get("tmax", "0").replace("p", ".").replace("n", "e-9")))


def show():
    data = rows()
    ok = [r for r in data if r.get("ok") and r.get("v(out)", {}).get("ok")]
    print("%d runs stored, %d usable\n" % (len(data), len(ok)))

    hdr = "%-6s %-5s %-7s %-6s %10s %10s %10s %10s %9s %9s %9s" % (
        "h(ns)", "method", "reltol", "load", "Vpp", "f(MHz)", "H2(dBc)",
        "H3(dBc)", "THD%", "settle", "envdev")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(ok, key=key):
        o = r["v(out)"]
        h = o["harm"]
        a = h["amp"]
        h2 = 20 * np.log10(a[1] / a[0]) if a[1] > 0 else float("-inf")
        h3 = 20 * np.log10(a[2] / a[0]) if a[2] > 0 else float("-inf")
        thd = 100 * np.sqrt(sum(x * x for x in a[1:])) / a[0]
        hn = float(r["tmax"].replace("p", ".").replace("n", "e-9")) * 1e9
        print("%-6.4f %-5s %-7s %-6s %10.5f %10.4f %10.2f %10.2f %9.2f %9.3f %9.1e" % (
            hn, r["method"], r["reltol"], r["rload"], o["vpp"], o["f_mhz"],
            h2, h3, thd, o["settle_s"] * 1e3, o["env_dev_after"]))

    print()
    print("=== amplitude convergence, per load (trap, reltol 1e-4) ===")
    for ld in ("2k", "10k"):
        s = {}
        for r in ok:
            if r["method"] == "trap" and r["reltol"] == "1e-4" and r["rload"] == ld:
                s[float(r["tmax"].replace("p", ".").replace("n", "e-9"))] = r["v(out)"]["vpp"]
        if len(s) < 2:
            print("  %-6s only %d point(s): %s" % (LOAD[ld], len(s), s))
            continue
        ks = sorted(s)
        print("  %-6s %s" % (LOAD[ld], "  ".join("%.4fn:%.5f" % (k * 1e9, s[k]) for k in ks)))
        for a, b in zip(ks, ks[1:]):
            d = s[b] - s[a]
            print("         %.4f -> %.4f ns : %+.5f V (%+.3f%%)" % (
                a * 1e9, b * 1e9, d, 100 * d / s[a]))
        if len(ks) >= 3:
            a, b, c = ks[-3], ks[-2], ks[-1]
            r1 = (s[c] - s[b]) / (s[b] - s[a]) if (s[b] - s[a]) != 0 else float("nan")
            print("         adjacent-difference ratio = %.3f  (0.5 => clean 1st order, 0.25 => 2nd)" % r1)

    print()
    print("=== load-to-load comparison at identical settings ===")
    seen = {}
    for r in ok:
        k = (r["method"], r["reltol"], float(r["tmax"].replace("p", ".").replace("n", "e-9")))
        seen.setdefault(k, {})[r["rload"]] = r["v(out)"]["vpp"]
    for k in sorted(seen):
        d = seen[k]
        if "2k" in d and "10k" in d:
            hn, m, rt = k[2] * 1e9, k[0], k[1]
            print("  %-5s h=%.4f ns reltol=%-5s : 2k=%.5f  10k=%.5f  ratio=+%.2f%%  10k vs 2.1 = %+.3f%%" % (
                m, hn, rt, d["2k"], d["10k"], 100 * (d["10k"] / d["2k"] - 1),
                100 * (d["10k"] / 2.1 - 1)))
        else:
            print("  %-5s h=%.4f ns reltol=%-5s : incomplete %s" % (k[0], k[2] * 1e9, k[1], list(d)))


if __name__ == "__main__":
    show()
