# -*- coding: utf-8 -*-
"""C3 fine rung: one more step below 0.125 ns, on a 3 ms window.

3 ms is enough: the envelope settles by ~1.8 ms in every run measured so far,
and 3 ms still gives >1 ms of steady state.  A 4 ms window at 0.0625 ns would
be 64M internal steps and took hours of wall time for no extra information.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3_runs as R
import c3lib as L

JOBS = []
for m in ("trap", "gear"):
    JOBS.append(("fine2_%s_0p0625n_rtol1e-4_2k" % m,
                 dict(method=m, maxord=2, reltol="1e-4", tmax="0.0625n",
                      tstop="3m", rload="2k")))

if __name__ == "__main__":
    R.run_batch(JOBS, os.path.join(L.RESDIR, "fine2.json"))
