# -*- coding: utf-8 -*-
"""C3: fill the RLC reference at h=0.125 ns for Q=17118 (both methods).

This rung is what turns the correction from anecdote into a test: at 0.25 ns
the RLC-predicted trap/gear gap matches the oscillator gap, but at 0.125 ns
the oscillator gap is -148 ppm, not -590 ppm.  If the RLC reference tracks
that collapse too, the correction is validated on two independent rungs.
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3lib as L
import c3_rlc2 as R2

OUT = os.path.join(L.RESDIR, "rlc2b.json")
JOBS = []
for m in ("trap", "gear"):
    JOBS.append((17118.0, "Q17118", m, "0p125n"))
    JOBS.append((17118.0, "Q17118", m, "0p0625n"))

if __name__ == "__main__":
    out = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(R2.do_ringdown, Q, nm, m, st, "1500u") for Q, nm, m, st in JOBS]
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out.append(r)
            L.json_dump(OUT, out)
    print("wrote", OUT)
