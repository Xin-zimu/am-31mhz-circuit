# -*- coding: utf-8 -*-
"""C3 controls: TSTEP vs TMAX, and the initial-disturbance question.

A. TSTEP control (this is the .tran parameter-position check)
   .tran TSTEP TSTOP TSTART TMAX.  Only TMAX sets the internal step.  Running
   the same TMAX=0.25 ns with TSTEP = 0.25 / 1 / 5 ns must give the same
   answer; if it does not, the C2 text's "change the first parameter" was
   right for the wrong reason.

B. Initial disturbance
   Hypothesis: the trap/gear split is two different stable states selected by
   the start-up, not two approximations of one state.  Test by starting the
   same numerical setup from (i) UIC as-is, (ii) UIC + injected current kick,
   (iii) no UIC (DC operating point start).
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

OUT = os.path.join(L.RESDIR, "control.json")
KICK = "IKICK 0 xl PULSE(0 20m 10n 1n 1n 500u 1m)"


def do(tag, **kw):
    net = L.build_cascade(tag, **kw)
    if not kw.get("uic", True):
        net = net.replace(" uic", "")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        d = L.read_raw(info["raw"])
        t = d["time"]
        m = L.measure(t, d["v(out)"])
        res = dict(ok=True, tag=tag, seconds=info["seconds"], cfg=kw, out=m,
                   ve=L.measure(t, d["v(e)"]), vb=L.measure(t, d["v(b)"]))
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, tag=tag, cfg=kw, error=str(e)[-600:])
        m = {}
    res["wall"] = round(time.monotonic() - t0, 1)
    print("%-26s %s" % (tag, ("f=%10.3f kHz Vpp=%8.5f" % (m["f_mhz"] * 1e3, m["vpp"]))
                        if m.get("ok") else "NONOSC/FAIL"), flush=True)
    return res


JOBS = [
    # A. TSTEP control, TMAX fixed at 0.25 ns
    ("ctl_tstep0p25n_trap", dict(method="trap", tmax="0.25n", tstep="0.25n", tstop="4m")),
    ("ctl_tstep1n_trap", dict(method="trap", tmax="0.25n", tstep="1n", tstop="4m")),
    ("ctl_tstep5n_trap", dict(method="trap", tmax="0.25n", tstep="5n", tstop="4m")),
    ("ctl_tmax1n_tstep1n_trap", dict(method="trap", tmax="1n", tstep="1n", tstop="4m")),
    # B. initial disturbance, same numerical setup
    ("ic_kick_trap", dict(method="trap", tmax="0.25n", tstop="4m", kick=KICK)),
    ("ic_kick_gear", dict(method="gear", tmax="0.25n", tstop="4m", kick=KICK)),
    ("ic_kickbig_trap", dict(method="trap", tmax="0.25n", tstop="4m",
                             kick="IKICK 0 xl PULSE(0 200m 10n 1n 1n 500u 1m)")),
    ("ic_kickbig_gear", dict(method="gear", tmax="0.25n", tstop="4m",
                             kick="IKICK 0 xl PULSE(0 200m 10n 1n 1n 500u 1m)")),
    ("ic_nouic_trap", dict(method="trap", tmax="0.25n", tstop="4m", uic=False)),
    ("ic_nouic_gear", dict(method="gear", tmax="0.25n", tstop="4m", uic=False)),
    # C. does gear start at 0.5 ns if the tank is pre-charged?
    ("ic_kickbig_gear_0p5n", dict(method="gear", tmax="0.5n", tstop="4m",
                                  kick="IKICK 0 xl PULSE(0 200m 10n 1n 1n 500u 1m)")),
]

if __name__ == "__main__":
    out = {}
    if os.path.exists(OUT):
        for r in L.json_load(OUT):
            out[r["tag"]] = r
    todo = [(t, k) for t, k in JOBS if t not in out]
    print("control.json: %d total, %d cached, %d to run" % (len(JOBS), len(out), len(todo)), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(do, t, **k): t for t, k in todo}
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out[r["tag"]] = r
            L.json_dump(OUT, sorted(out.values(), key=lambda x: x["tag"]))
    print("done")
