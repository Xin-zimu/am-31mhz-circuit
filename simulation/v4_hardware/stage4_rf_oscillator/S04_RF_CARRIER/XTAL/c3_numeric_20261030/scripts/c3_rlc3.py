# -*- coding: utf-8 -*-
"""C3 re-run of the driven RLC cases with the corrected amplitude analysis."""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3lib as L
import c3_rlc as R
import c3_rlc2 as R2

OUT = os.path.join(L.RESDIR, "rlc2_driven.json")
JOBS = []
for nm, Q in [("Q1000", 1000.0), ("Q17118", 17118.0)]:
    for m in ("trap", "gear"):
        for st in ("0p25n", "0p5n"):
            JOBS.append((Q, nm, m, st))
JOBS += [(50.0, "Q50", m, "0p25n") for m in ("trap", "gear")]
JOBS += [(200.0, "Q200", m, "0p25n") for m in ("trap", "gear")]

if __name__ == "__main__":
    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(R2.do_driven, Q, nm, m, st) for Q, nm, m, st in JOBS]
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out.append(r)
            L.json_dump(OUT, out)
    print("wrote", OUT)
