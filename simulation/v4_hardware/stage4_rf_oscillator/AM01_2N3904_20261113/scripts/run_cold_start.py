# -*- coding: utf-8 -*-
"""Physical cold-start check with a real 0..4 V unipolar square wave.

This run does not use the capacitor solution or uic. It is deliberately long
enough for the 100 nF/RBB network to settle, and its final state is compared
with the periodic-shooting result.
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
OUT = L.RESULTS / "cold_start.json"


def main():
    raw = L.RAWS / "cold_start_4v_d50.raw"
    log = L.LOGS / "cold_start_4v_d50.log"
    text = L.build_netlist(PARAMS, 4.0, 0.5, 2000.0, cold=True,
                           stop_us=60000.0, tmax_ns=20.0, raw_name=raw.as_posix())
    text = text.replace(
        "save v(src) v(rfatt) v(b1) v(c1) v(x) v(b2) v(e2) v(mod) v(b2ac) v(out) i(vsup)",
        "save v(b2ac) v(b2) v(mod)")
    cir = L.NETLISTS / "cold_start_4v_d50.cir"
    cir.write_text(text, encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=600)
    if proc.returncode != 0 or not raw.exists():
        raise RuntimeError("Cold-start run failed; see " + str(log))
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
    fit_mask = (t >= 5e-3) & (t <= 55e-3)
    # Window-average the exponential so the fitted tau is not biased by RF.
    tfit, efit = [], []
    for start_ms in range(5, 55):
        mask = (t >= start_ms * 1e-3) & (t < (start_ms + 1) * 1e-3)
        value = abs(L.time_mean(t, error, mask))
        if value > 1e-9:
            tfit.append(start_ms * 1e-3)
            efit.append(value)
    slope, intercept, rvalue, pvalue, stderr = linregress(tfit, np.log(efit))
    tau = -1.0 / slope
    last = windows[-1]
    solve = L.periodic_cap_solve(PARAMS, 4.0, 0.5, 2000.0, "cold_ref", verbose=False)
    result = {
        "conditions": "real 0..4 V unipolar 20 kHz square, 50%, RL=2k, no .ic, no uic",
        "duration_ms": 60.0,
        "max_step_ns": 20.0,
        "windows": windows,
        "fitted_tau_ms": 1000.0 * tau,
        "fit_r_squared": float(rvalue ** 2),
        "final_mean_coupling_error_mv": last["mean_coupling_error_mv"],
        "shooting_vcap_v": solve["vcap"],
        "shooting_residual_mv": 1000.0 * solve["residual_v"],
        "final_minus_shooting_b2_mv": 1000.0 * (last["mean_b2_v"] - solve["vcap"]),
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
    print("final error mV", last["mean_coupling_error_mv"], "shooting", result["shooting_vcap_v"])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
