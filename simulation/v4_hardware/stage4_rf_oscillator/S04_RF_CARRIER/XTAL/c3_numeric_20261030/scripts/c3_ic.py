# -*- coding: utf-8 -*-
"""C3: initial-disturbance test, corrected design.

The first attempt used IKICK PULSE(0 20m / 200m ...) - 20 to 200 mA injected
into the crystal node.  That is not a small disturbance: it drove the circuit
into a completely different relaxation mode (12.9 MHz, 4.08 Vpp, and at 0.5 ns
6.1 kHz).  Those runs are recorded as INVALID controls, not as evidence.

Correct design: perturb the start of oscillation so slightly that the circuit
still starts in its normal small-signal regime, and see whether the settled
state depends on the perturbation at all.  Two knobs that do this safely:
  * .ic on the crystal series capacitor (sets a small initial charge)
  * trtol / reltol, which perturb the startup trajectory without changing
    the physics
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

OUT = os.path.join(L.RESDIR, "ic.json")


def do(tag, **kw):
    net = L.build_cascade(tag, **kw)
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        d = L.read_raw(info["raw"])
        t = d["time"]
        m = L.measure(t, d["v(out)"])
        res = dict(ok=True, tag=tag, seconds=info["seconds"], cfg=kw, out=m)
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, tag=tag, cfg=kw, error=str(e)[-600:])
        m = {}
    res["wall"] = round(time.monotonic() - t0, 1)
    print("%-30s %s" % (tag, ("f=%10.3f kHz Vpp=%8.5f settle=%.3fms" % (
        m["f_mhz"] * 1e3, m["vpp"], m["settle_s"] * 1e3)) if m.get("ok") else "NONOSC/FAIL"),
        flush=True)
    return res


JOBS = []
for m in ("trap", "gear"):
    # initial charge on the crystal capacitor: 0 (as-is), 0.5 V, 2 V
    for v, ic in (("v0", ""), ("v05", ".ic v(xc)=0.5"), ("v20", ".ic v(xc)=2.0"),
                  ("vm05", ".ic v(xc)=-0.5")):
        JOBS.append(("ic_%s_%s_0p25n" % (m, v), dict(method=m, tmax="0.25n", tstop="4m", ic=ic)))
    # trajectory perturbation without touching physics
    for tt in ("1", "20"):
        JOBS.append(("ic_%s_trtol%s" % (m, tt), dict(method=m, tmax="0.25n", tstop="4m",
                                                     trtol=int(tt))))

if __name__ == "__main__":
    out = {}
    if os.path.exists(OUT):
        for r in L.json_load(OUT):
            out[r["tag"]] = r
    todo = [(t, k) for t, k in JOBS if t not in out]
    print("ic.json: %d total, %d cached, %d to run" % (len(JOBS), len(out), len(todo)), flush=True)
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
