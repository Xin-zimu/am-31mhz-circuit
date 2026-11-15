# -*- coding: utf-8 -*-
"""Cold-start coupling check with the 31 MHz carrier disabled.

The 100 nF/RBB settling is a low-frequency, bias-network process. Turning off
only the carrier removes the 31 MHz timestep burden and the coarse-step
rectification floor, while leaving the coupling network and Q2 bias intact.
A separate short carrier-on run covers RF startup.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import linregress

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
OUT = L.RESULTS / "cold_coupling_60ms.json"


def main():
    raw = L.RAWS / "cold_coupling_60ms.raw"
    log = L.LOGS / "cold_coupling_60ms.log"
    text = L.build_netlist(PARAMS, 4.0, 0.5, 2000.0, cold=True, carrier=False,
                           stop_us=60000.0, tmax_ns=10000.0, raw_name=raw.as_posix())
    text = text.replace(
        "save v(src) v(rfatt) v(b1) v(c1) v(x) v(b2) v(e2) v(mod) v(b2ac) v(out) i(vsup)",
        "save v(b2ac) v(b2) v(mod)")
    cir = L.NETLISTS / "cold_coupling_60ms.cir"
    cir.write_text(text, encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    if proc.returncode != 0 or not raw.exists():
        raise RuntimeError("Cold coupling run failed; see " + str(log))
    data = L.read_raw(raw)
    t = data["time"]
    error = data["v(b2ac)"] - data["v(b2)"]
    windows = []
    for start_ms in range(0, 60, 5):
        mask = (t >= start_ms * 1e-3) & (t < (start_ms + 5) * 1e-3)
        windows.append({
            "window_ms": [start_ms, start_ms + 5],
            "mean_coupling_error_mv": 1000.0 * L.time_mean(t, error, mask),
            "mean_b2_v": L.time_mean(t, data["v(b2)"], mask),
            "mean_b2ac_v": L.time_mean(t, data["v(b2ac)"], mask),
        })
    tfit, efit = [], []
    for start_ms in range(5, 50):
        mask = (t >= start_ms * 1e-3) & (t < (start_ms + 1) * 1e-3)
        value = abs(L.time_mean(t, error, mask))
        if value > 1e-7:
            tfit.append(start_ms * 1e-3)
            efit.append(value)
    slope, intercept, rvalue, pvalue, stderr = linregress(tfit, np.log(efit))
    tau = -1.0 / slope
    result = {
        "conditions": "real cold start, 0..4 V unipolar 20 kHz/50%, carrier source disabled",
        "duration_ms": 60.0,
        "max_step_us": 10.0,
        "windows": windows,
        "fitted_tau_ms": 1000.0 * tau,
        "fit_r_squared": float(rvalue ** 2),
        "final_mean_coupling_error_mv": windows[-1]["mean_coupling_error_mv"],
        "final_mean_b2_v": windows[-1]["mean_b2_v"],
        "netlist": str(cir),
        "netlist_sha256": L.sha256(cir),
        "raw_sha256": L.sha256(raw),
        "raw_bytes": raw.stat().st_size,
        "log_sha256": L.sha256(log),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in windows:
        print(row)
    print("tau_ms", 1000 * tau, "R2", rvalue ** 2)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
