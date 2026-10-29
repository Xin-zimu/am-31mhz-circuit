# -*- coding: utf-8 -*-
"""C3 run driver. One numerical parameter changes per run.

usage: python c3_runs.py <phase>
phases: base | reltol | ic | rlc | lt | tenk | all
Results accumulate in results/<phase>.json (resumable: finished runs are skipped).
"""
import os
import sys
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

NODES = ("v(out)", "v(e)", "v(b)")
MAXWORKERS = 3


def measure_all(raw_path):
    d = L.read_raw(raw_path)
    t = d["time"]
    out = dict(n_pts=int(t.size), t_end=float(t[-1]),
               dt_min=float(np.min(np.diff(t))), dt_max=float(np.max(np.diff(t))))
    for nd in NODES:
        if nd in d:
            mm = L.measure(t, d[nd])
            if mm.get("ok"):
                xs, ys = L.amplitude_series(t, d[nd])
                mm["env_x"] = [round(float(x), 9) for x in xs[::4]]
                mm["env_y"] = [round(float(y), 6) for y in ys[::4]]
                mm["growth_rate"] = L.growth_rate(xs, ys)
            out[nd] = mm
    return out


def run_one(cfg, tag):
    """cfg: kwargs for build_cascade. Returns result dict."""
    name = tag
    t0 = time.monotonic()
    net = L.build_cascade(name, **cfg)
    p = L.write_netlist(name, net)
    rec = dict(tag=name, cfg={k: v for k, v in cfg.items() if k != "save"},
               cir=p, cir_sha256=L.sha256(p))
    try:
        info = L.run_ngspice(p, name + ".raw")
        rec.update(seconds=info["seconds"], raw_bytes=info["raw_bytes"])
        rec.update(measure_all(info["raw"]))
        os.remove(info["raw"])
        rec["ok"] = True
    except Exception as e:
        rec["ok"] = False
        rec["error"] = str(e)[-2000:]
        print("FAIL", name, rec["error"][:400], flush=True)
    rec["wall_s"] = round(time.monotonic() - t0, 1)
    print("%-34s %s %6.1fs %s" % (name, "ok " if rec["ok"] else "ERR",
                                  rec["wall_s"],
                                  ("%.4f MHz %.5f Vpp" % (rec["v(out)"]["f_mhz"], rec["v(out)"]["vpp"]))
                                  if rec.get("ok") and rec.get("v(out)", {}).get("ok") else ""),
          flush=True)
    return rec


def run_batch(jobs, out_path):
    done = {}
    if os.path.exists(out_path):
        for r in L.json_load(out_path):
            done[r["tag"]] = r
    todo = [(tag, cfg) for tag, cfg in jobs if tag not in done]
    print("phase %s: %d total, %d cached, %d to run" % (os.path.basename(out_path), len(jobs), len(done), len(todo)), flush=True)
    if todo:
        with ThreadPoolExecutor(max_workers=MAXWORKERS) as ex:
            futs = {ex.submit(run_one, cfg, tag): tag for tag, cfg in todo}
            for f in futs:
                try:
                    r = f.result()
                    done[r["tag"]] = r
                except Exception:
                    traceback.print_exc()
                L.json_dump(out_path, sorted(done.values(), key=lambda x: x["tag"]))
    L.json_dump(out_path, sorted(done.values(), key=lambda x: x["tag"]))
    return done


# ---------------------------------------------------------------- phases ----
def phase_base():
    jobs = []
    for m in ("trap", "gear"):
        for st in ("2n", "1n", "0p5n", "0p25n", "0p125n"):
            tmax = st.replace("p", ".")
            tag = "base_%s_%s_rtol1e-4_2k" % (m, st)
            jobs.append((tag, dict(method=m, maxord=2, reltol="1e-4",
                                   tmax=tmax, tstop="8m", rload="2k")))
    run_batch(jobs, os.path.join(L.RESDIR, "base.json"))


def phase_reltol():
    jobs = []
    for m in ("trap", "gear"):
        for rt in ("1e-3", "1e-4", "1e-5", "1e-6"):
            tag = "rtol_%s_%s_0p25n_2k" % (m, rt.replace("e-", "e"))
            jobs.append((tag, dict(method=m, maxord=2, reltol=rt,
                                   tmax="0.25n", tstop="8m", rload="2k")))
    run_batch(jobs, os.path.join(L.RESDIR, "reltol.json"))


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "base"
    {"base": phase_base, "reltol": phase_reltol}[phase]()
