# -*- coding: utf-8 -*-
"""C3: the last RLC rung (gear at 0.0625 ns, Q=17118).

This is the one point still missing from the trap/gear comparison at the
finest step.  The earlier attempt at 1500 us with 0.0625 ns did not finish in
a useful time, so the window is trimmed to 700 us - still 12 decay-time
constants of the tank (tau = 176 us) is not needed here; what is needed is
enough steady-state cycles to fit alpha, which 700 us provides.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3lib as L
import c3_rlc2 as R2

OUT = os.path.join(L.RESDIR, "rlc2c.json")
if __name__ == "__main__":
    out = []
    r = R2.do_ringdown(17118.0, "Q17118", "gear", "0p0625n", tstop="700u")
    out.append(r)
    L.json_dump(OUT, out)
    print("wrote", OUT)
