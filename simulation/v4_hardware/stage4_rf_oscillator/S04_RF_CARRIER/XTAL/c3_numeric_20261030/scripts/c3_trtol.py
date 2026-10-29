# -*- coding: utf-8 -*-
"""C3: is the gear trtol=1 offset repeatable, or a one-off?

One run showing +0.32% is not evidence of sensitivity - it could be timestep
noise.  Repeat it, and bracket it with neighbouring trtol values, so the
report states a measured trend rather than a single point.
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3lib as L

OUT = os.path.join(L.RESDIR, "trtol.json")


def do(tag, method, trtol, tstop="4m"):
    net = L.build_cascade(tag, method=method, maxord=2, reltol="1e-4",
                          trtol=trtol, tmax="0.25n", tstop=tstop)
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        d = L.read_raw(info["raw"])
        t = d["time"]
        m = L.measure(t, d["v(out)"])
        os.remove(info["raw"])
        r = dict(ok=True, tag=tag, method=method, trtol=trtol, out=m,
                 seconds=info["seconds"])
        print("%-20s trtol=%-3d Vpp=%.5f  f=%.4f kHz" % (
            method, trtol, m["vpp"], m["f_mhz"] * 1e3), flush=True)
    except Exception as e:
        r = dict(ok=False, tag=tag, method=method, trtol=trtol, error=str(e)[-500:])
        print("%-20s trtol=%-3d FAIL" % (method, trtol), flush=True)
    r["wall"] = round(time.monotonic() - t0, 1)
    return r


JOBS = []
for tt in (1, 2, 3, 7, 20):
    JOBS.append(("tt_gear_r%d" % tt, "gear", tt))
for tt in (1, 2, 3, 7, 20):
    JOBS.append(("tt_trap_r%d" % tt, "trap", tt))
# duplicate the outlier to test repeatability
JOBS.append(("tt_gear_r1b", "gear", 1))

if __name__ == "__main__":
    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(do, *j) for j in JOBS]
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out.append(r)
            L.json_dump(OUT, out)
    print("wrote", OUT)
