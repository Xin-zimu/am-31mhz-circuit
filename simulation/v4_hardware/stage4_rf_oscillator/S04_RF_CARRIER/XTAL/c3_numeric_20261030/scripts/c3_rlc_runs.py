# -*- coding: utf-8 -*-
"""C3 step 4b: run the analytic RLC references through ngspice.

Everything here is linear and has a closed-form answer, so whatever the
integrator does is pure numerical error: frequency error (phase error per
step) and amplitude error (numerical damping).

ring-down: v(0)=1 V on C, i_L(0)=0.  Exact f and exact decay rate alpha.
driven   : current source at f0 into the same tank, steady state |v| = I*R.
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L
import c3_rlc as R

OUT = os.path.join(L.RESDIR, "rlc.json")
STEPS = ["2n", "0p5n", "0p125n"]
METHODS = ["trap", "gear"]


def do_ringdown(Q, nm, method, st):
    tag = "rd_%s_%s_%s" % (nm, method, st)
    tmax = st.replace("p", ".")
    net = R.net_ringdown(tag, Q, method, 2, "1e-4", tmax, "20u", raw=tag + ".raw")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        res = R.analyse_ringdown(info["raw"], Q)
        os.remove(info["raw"])
        res.update(ok=res.get("ok", False), seconds=info["seconds"])
    except Exception as e:
        res = dict(ok=False, error=str(e)[-800:])
    res.update(tag=tag, case=nm, Q=Q, method=method, tmax=tmax, wall=round(time.monotonic() - t0, 1))
    print("%-26s %s" % (tag, ("df=%9.2f ppm  dalpha=%8.2f%%  Qsim=%8.2f" %
          (res.get("df_ppm", float("nan")), res.get("dalpha_pct", float("nan")),
           res.get("Q_sim", float("nan")))) if res.get("ok") else res.get("error", "")[:120]), flush=True)
    return res


def do_driven(Q, nm, method, st):
    tag = "dr_%s_%s_%s" % (nm, method, st)
    tmax = st.replace("p", ".")
    net = R.net_driven(tag, Q, method, 2, "1e-4", tmax, "200u", raw=tag + ".raw")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        res = R.analyse_driven(info["raw"], Q)
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, error=str(e)[-800:])
    res.update(tag=tag, case=nm, Q=Q, method=method, tmax=tmax, wall=round(time.monotonic() - t0, 1))
    print("%-26s %s" % (tag, ("amp_err=%+8.3f%%  f=%12.6f MHz  phase=%6.2f deg" %
          (res.get("amp_err_pct", float("nan")), res.get("f_sim_MHz", float("nan")),
           res.get("phase_deg", float("nan")))) if res.get("ok") else res.get("error", "")[:120]), flush=True)
    return res


def main():
    jobs = []
    for nm, Q in R.CASES:
        for m in METHODS:
            for st in STEPS:
                jobs.append((do_ringdown, Q, nm, m, st))
    for nm, Q in R.CASES:
        for m in METHODS:
            jobs.append((do_driven, Q, nm, m, "0p25n"))
    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(f, *a) for f, *a in jobs]
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out.append(r)
            L.json_dump(OUT, out)
    L.json_dump(OUT, out)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    main()
