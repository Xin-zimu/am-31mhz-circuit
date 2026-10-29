# -*- coding: utf-8 -*-
"""C4 dual-load convergence re-test.

Scope (user 2026-10-30): the only two questions still open for S04 are
  (1) does the 10 kOhm load stay inside 1.9-2.1 Vpp at fine step, and
  (2) is H2 still over -20 dBc on a converged grid.

Design decisions, all justified by C3:
  * trap is the primary method.  C3 showed trap's |R|=1 (no numerical damping)
    while gear's damping collapses the amplitude.  gear is kept only as a
    cross-check at one step.
  * TMAX is the accuracy knob; TSTEP and TSTART only control what is written.
    C3 verified TSTEP 0.25/1/5 ns give bit-identical results, so the steady
    window is saved at 0.25 ns while the solver still runs at 0.0625 ns.
    That is what keeps the raw files small.
  * Only v(out) and v(e) are saved - the harmonics and amplitudes live there.
  * No component value is touched. RE1 stays 56 ohm. Topology unchanged.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c4env          # noqa: F401  (sets up paths)
import c3lib as L

OUT = os.path.join(L.RESDIR, "c4_dual.json")
TSTOP = "5m"        # 5 ms: settles by ~1.8 ms, leaves >3 ms of steady state
TSTART = "3m"       # only the last 2 ms is written to disk
TSTEP = "0.25n"     # output interval only - proven not to affect accuracy (C3 S7)
SAVE = "v(out) v(e)"


def do(tag, method="trap", tmax="0.125n", reltol="1e-4", rload="2k",
       tstop=TSTOP, tstart=TSTART, tstep=TSTEP, maxtime=7200):
    net = L.build_cascade(tag, method=method, maxord=2, reltol=reltol,
                          tmax=tmax, tstep=tstep, tstop=tstop, tstart=tstart,
                          rload=rload, save=SAVE)
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw", timeout=maxtime)
        d = L.read_raw(info["raw"])
        t = d["time"]
        res = dict(ok=True, tag=tag, method=method, tmax=tmax, reltol=reltol,
                   rload=rload, tstop=tstop, tstart=tstart, tstep=tstep,
                   seconds=info["seconds"], raw_mb=round(info["raw_bytes"] / 1e6, 1),
                   n_pts=int(t.size),
                   tout=dict(start=float(t[0]), end=float(t[-1])))
        for nd in ("v(out)", "v(e)"):
            if nd in d:
                res[nd] = L.measure(t, d[nd])
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, tag=tag, error=str(e)[-800:])
    res["wall"] = round(time.monotonic() - t0, 1)
    o = res.get("v(out)", {})
    if o.get("ok"):
        h = o["harm"]
        print("%-28s %s  Vpp=%.5f  f=%.4f MHz  H2=%.2f%%  H3=%.2f%%  THD=%.2f%%  (%.0fs)" % (
            tag, rload, o["vpp"], o["f_mhz"],
            100 * h["amp"][1] / h["amp"][0], 100 * h["amp"][2] / h["amp"][0],
            100 * np.sqrt(sum(a * a for a in h["amp"][1:])) / h["amp"][0],
            res["wall"]), flush=True)
    else:
        print("%-28s %s  FAILED %s" % (tag, rload, str(res.get("error", ""))[:120]), flush=True)
    return res


JOBS = [
    # --- primary: trap, both loads, two fine steps, identical settings ---
    ("c4_trap_0p125n_2k",  dict(tmax="0.125n", rload="2k")),
    ("c4_trap_0p125n_10k", dict(tmax="0.125n", rload="10k")),
    ("c4_trap_0p0625n_2k", dict(tmax="0.0625n", rload="2k")),
    ("c4_trap_0p0625n_10k", dict(tmax="0.0625n", rload="10k")),
    # --- reltol check at the middle step: C2 said reltol matters most ---
    ("c4_trap_0p125n_2k_rtol1e5",  dict(tmax="0.125n", rload="2k", reltol="1e-5")),
    ("c4_trap_0p125n_10k_rtol1e5", dict(tmax="0.125n", rload="10k", reltol="1e-5")),
    # --- gear cross-check at one step, both loads ---
    ("c4_gear_0p125n_2k",  dict(method="gear", tmax="0.125n", rload="2k")),
    ("c4_gear_0p125n_10k", dict(method="gear", tmax="0.125n", rload="10k")),
]

if __name__ == "__main__":
    out = {}
    if os.path.exists(OUT):
        for r in L.json_load(OUT):
            out[r["tag"]] = r
    todo = [(t, k) for t, k in JOBS if t not in out or not out[t].get("ok")]
    print("c4_dual.json: %d total, %d cached, %d to run" % (len(JOBS), len(out), len(todo)), flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(do, t, **k): t for t, k in todo}
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, tag="?", error=str(e))
            out[r["tag"]] = r
            L.json_dump(OUT, sorted(out.values(), key=lambda x: str(x.get("tag"))))
    print("done", OUT)