# -*- coding: utf-8 -*-
"""C3 pilot: reproduce the C2 baseline exactly and time it."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

name = "pilot_trap_0p25n_rtol1e-4"
net = L.build_cascade(name, method="trap", maxord=2, reltol="1e-4",
                      tmax="0.25n", tstop="8m", rload="2k")
p = L.write_netlist(name, net)
print("netlist:", p)
info = L.run_ngspice(p, name + ".raw")
print("run:", info["seconds"], "s, raw", info["raw_bytes"], "bytes")
d = L.read_raw(info["raw"])
print("vars:", list(d.keys()), "npt:", d[list(d.keys())[0]].size)
t = d["time"] if "time" in d else d[list(d.keys())[0]]
print("t range", t[0], t[-1], "dt min/max", np.min(np.diff(t)), np.max(np.diff(t)))
for node in ("v(out)", "v(e)", "v(b)"):
    if node not in d: continue
    m = L.measure(t, d[node])
    print(node, "f=%.3f MHz vpp=%.5f settle=%.4f ms dev=%.2e" % (
        m["f_mhz"], m["vpp"], m["settle_s"]*1e3, m["env_dev_after"]))
    print("   harm:", ["%.2f%%" % (100*a/m["harm"]["amp"][0]) for a in m["harm"]["amp"][:4]],
          "rms_resid", "%.2e" % m["harm"]["rms_resid"])
