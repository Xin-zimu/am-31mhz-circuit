# -*- coding: utf-8 -*-
"""C3 addendum: RLC reference at the crystal's actual branch Q.

The crystal branch in c2_two_load.cir is RM=30, LM=2.637 mH, CM=10 fF:
  fs = 30.992622 MHz,  Q = (1/RM)*sqrt(LM/CM) = 17118,  tau = 176 us.
The first RLC sweep only reached Q=1000.  Numerical damping grows steeply with
Q, so the reference has to be taken at the operating Q before it can explain
the oscillator.

Also fills the h=0.25 ns rung for the lower Q values so the trap/gear gap can
be compared with the oscillator at the same step.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L
import c3_rlc as R

OUT = os.path.join(L.RESDIR, "rlc2.json")
CASES = [("Q1000", 1000.0), ("Q17118", 17118.0)]


def do_ringdown(Q, nm, method, st, tstop="1500u"):
    tag = "rd2_%s_%s_%s" % (nm, method, st)
    tmax = st.replace("p", ".")
    net = R.net_ringdown(tag, Q, method, 2, "1e-4", tmax, tstop, raw=tag + ".raw")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        res = R.analyse_ringdown(info["raw"], Q)
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, error=str(e)[-600:])
    res.update(tag=tag, case=nm, Q=Q, method=method, tmax=tmax,
               wall=round(time.monotonic() - t0, 1))
    print("%-28s %s" % (tag, ("df=%+11.2f ppm  dalpha=%+9.2f%%  Qsim=%9.1f" %
          (res.get("df_ppm", float("nan")), res.get("dalpha_pct", float("nan")),
           res.get("Q_sim", float("nan")))) if res.get("ok") else res.get("error", "")[:100]), flush=True)
    return res


def do_driven(Q, nm, method, st, tstop="4m"):
    tag = "dr2_%s_%s_%s" % (nm, method, st)
    tmax = st.replace("p", ".")
    net = R.net_driven(tag, Q, method, 2, "1e-4", tmax, tstop, raw=tag + ".raw")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        res = R.analyse_driven(info["raw"], Q)
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, error=str(e)[-600:])
    res.update(tag=tag, case=nm, Q=Q, method=method, tmax=tmax,
               wall=round(time.monotonic() - t0, 1))
    print("%-28s %s" % (tag, ("amp_err=%+9.3f%%  phase=%8.2f deg" %
          (res.get("amp_err_pct", float("nan")), res.get("phase_deg", float("nan"))))
          if res.get("ok") else res.get("error", "")[:100]), flush=True)
    return res


JOBS = []
for nm, Q in CASES:
    for m in ("trap", "gear"):
        for st in ("0p25n", "0p5n"):
            JOBS.append((do_ringdown, Q, nm, m, st))
            JOBS.append((do_driven, Q, nm, m, st))

if __name__ == "__main__":
    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(f, *a) for f, *a in JOBS]
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out.append(r)
            L.json_dump(OUT, out)
    L.json_dump(OUT, out)
    print("wrote", OUT, len(out))
