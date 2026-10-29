# -*- coding: utf-8 -*-
"""C3 hypotheses 2 and 3: startup length, and initial-condition sensitivity.

H2  "gear just needs longer to settle"
      -> run gear at 0.5 ns and 1 ns for 32 ms and look for any growth at all.
      -> run both methods at 2/4/8/16 ms and compare the late-window answer.

H3  "two different stable states exist"
      -> start the same run from different initial disturbances and see whether
         the settled amplitude/frequency depends on the start.

Control:
      -> tstep only sets the OUTPUT interval; tmax sets the internal step.
         Running 0.25 ns with tstep 0.25n / 1n / 5n must give the same answer.
         This is the .tran parameter-position check the C2 text got wrong.
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

OUT = os.path.join(L.RESDIR, "window.json")


def late_window(t, v, frac=0.25):
    t0 = t[0] + (1.0 - frac) * (t[-1] - t[0])
    m = t >= t0
    tt, vv = t[m], v[m]
    env = L.cycle_envelope(tt, vv)
    if env is None:
        return dict(ok=False, reason="no oscillation", vpp=float(vv.max() - vv.min()))
    tc_env, amp_env, per_env, tc = env
    f, resid = L.fit_frequency(tc)
    tail = amp_env[-max(5, amp_env.size // 10):]
    return dict(ok=True, f_mhz=f / 1e6, vpp=float(vv.max() - vv.min()),
                vpp_cycle=float(np.mean(tail)),
                env_ptp_pct=float((tail.max() - tail.min()) / np.mean(tail) * 100),
                n_cycles=int(amp_env.size), resid_s=resid)


def full_growth(t, v, nbins=200):
    xs, ys = L.amplitude_series(t, v, nbins=nbins)
    return dict(t=[round(float(x), 6) for x in xs],
                a=[round(float(y), 6) for y in ys],
                growth=L.growth_rate(xs, ys))


def do(tag, method, tstop, tstep="0.25n", tmax="0.25n", ic="", kick="", uic=True,
       rload="2k", reltol="1e-4"):
    net = L.build_cascade(tag, method=method, maxord=2, reltol=reltol, tmax=tmax,
                          tstep=tstep, tstop=tstop, rload=rload, ic=ic, kick=kick)
    if not uic:
        net = net.replace(" uic", "")
    p = L.write_netlist(tag, net)
    t0 = time.monotonic()
    try:
        info = L.run_ngspice(p, tag + ".raw")
        d = L.read_raw(info["raw"])
        t = d["time"]
        res = dict(ok=True, tag=tag, method=method, tstop=tstop, tstep=tstep, tmax=tmax,
                   uic=uic, ic=ic, kick=kick, rload=rload, reltol=reltol,
                   seconds=info["seconds"], n_pts=int(t.size),
                   late=late_window(t, d["v(out)"]),
                   mid=late_window(t, d["v(out)"], frac=0.5),
                   growth=full_growth(t, d["v(out)"]))
        for nd in ("v(e)", "v(b)"):
            res[nd] = late_window(t, d[nd])
        os.remove(info["raw"])
    except Exception as e:
        res = dict(ok=False, tag=tag, method=method, tstop=tstop, error=str(e)[-600:])
    res["wall"] = round(time.monotonic() - t0, 1)
    lt = res.get("late", {})
    print("%-28s %-4s %-6s %s" % (tag, method, tstop,
          ("f=%10.3f kHz vpp=%8.5f envptp=%.2f%%" % (lt["f_mhz"] * 1e3, lt["vpp"], lt["env_ptp_pct"]))
          if lt.get("ok") else ("NONOSC vpp=%.2e" % lt.get("vpp", 0.0))), flush=True)
    return res


JOBS = []
# H2a: window length
for m in ("trap", "gear"):
    for ts in ("2m", "4m", "8m", "16m"):
        JOBS.append(("win_%s_%s" % (m, ts), dict(method=m, tstop=ts)))
# H2b: does gear ever start at a coarser step, given 32 ms?
JOBS.append(("slow_gear_0p5n_32m", dict(method="gear", tmax="0.5n", tstep="1n", tstop="32m")))
JOBS.append(("slow_gear_1n_32m", dict(method="gear", tmax="1n", tstep="2n", tstop="32m")))
JOBS.append(("slow_trap_0p5n_32m", dict(method="trap", tmax="0.5n", tstep="1n", tstop="32m")))
# H3: initial disturbance
KICK = "IKICK 0 xl PULSE(0 1m 10n 1n 1n 500u 1m)"
for m in ("trap", "gear"):
    JOBS.append(("kick_%s_0p25n" % m, dict(method=m, tstop="8m", kick=KICK)))
    JOBS.append(("kickbig_%s_0p25n" % m, dict(method=m, tstop="8m",
                 kick="IKICK 0 xl PULSE(0 20m 10n 1n 1n 500u 1m)")))
    JOBS.append(("nouic_%s_0p25n" % m, dict(method=m, tstop="8m", uic=False)))
# control: tstep is output only
JOBS.append(("tstep_trap_1n_8m", dict(method="trap", tstop="8m", tstep="1n")))
JOBS.append(("tstep_trap_5n_8m", dict(method="trap", tstop="8m", tstep="5n")))


def main():
    out = {}
    if os.path.exists(OUT):
        for r in L.json_load(OUT):
            out[r["tag"]] = r
    todo = [(t, k) for t, k in JOBS if t not in out]
    print("window.json: %d total, %d cached, %d to run" % (len(JOBS), len(out), len(todo)), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(do, tag, **kw): tag for tag, kw in todo}
        for f in futs:
            try:
                r = f.result()
            except Exception as e:
                r = dict(ok=False, error=str(e))
            out[r["tag"]] = r
            L.json_dump(OUT, sorted(out.values(), key=lambda x: x["tag"]))
    print("done", OUT)


if __name__ == "__main__":
    main()
