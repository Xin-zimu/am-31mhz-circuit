# -*- coding: utf-8 -*-
"""AM-02.3 step 6: acceptance matrix for the recommended second stage.

Levels 1/2/3/4 Vpp x duty 10/30/50 % x 50 ohm || 10 pF, through the frozen
AM-01 and the frozen scheme A. Reports the envelope, the modulation index,
the carrier THD, the operating region and the supply power for every point.
A second sweep repeats the 50 % points on 2 kOhm || 10 pF so the stage is not
qualified on one load only.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

CONFIGS = {
    "S3": ({"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0, "rea": 100.0,
            "lrfc": 2.2e-6, "reb": 180.0}, [50.0, 2000.0]),
    "S6": ({"rbat": 2.2e3, "rbab": 1.1e3, "rax": 8.0, "rea": 39.0,
            "lm": 0.82e-6, "cm": 68e-12, "rser": 10.0,
            "ltank": 0.47e-6, "ct1": 100e-12, "ct2": 56e-12}, [50.0]),
}
LEVELS = [1.0, 2.0, 3.0, 4.0]
DUTIES = [0.10, 0.30, 0.50]


def run_point(top, stage, load, amp, duty):
    tag = f"mx_{top}_{int(load)}_{amp:g}_{int(duty*100)}"
    solve = M.solve_cap(top, stage, amp, duty, tag=tag, stop_us=45.0, max_iter=4)
    state = dict(solve["op"]["nodes"])
    state["b2ac"] = -amp * duty + solve["vcap"]
    M.run(tag, M.build(top, stage, amp, duty, state=state, stop_us=128.0,
                       raw_name=tag + ".raw"), timeout=900)
    m = M.measure(M.RESULTS / (tag + ".raw"), top, duty, p0_us=75.0, load_r=load)
    Path(M.RESULTS / (tag + ".raw")).unlink(missing_ok=True)
    m.update({"config": top, "amp_vpp": amp, "cap_v": solve["vcap"],
              "cap_residual_mv": 1e3 * solve["residual"],
              "netlist": str(M.NETLISTS / (tag + ".cir")),
              "cir_sha256": M.sha256(M.NETLISTS / (tag + ".cir"))})
    return m


def main():
    rows = []
    for name, (stage, loads) in CONFIGS.items():
        for load in loads:
            for amp in LEVELS:
                duties = DUTIES if load == 50.0 else [0.5]
                for duty in duties:
                    print(f"{name} {load:g}ohm {amp:g}Vpp {duty:.0%}", flush=True)
                    try:
                        m = run_point(name, stage, load, amp, duty)
                    except Exception as exc:
                        print("  FAILED", exc)
                        continue
                    rows.append(m)
                    print(f"  out {m['vpp_high']*1e3:7.1f}/{m['vpp_low']*1e3:7.1f} mVpp "
                          f"m={100*m['modulation_index']:6.2f}% "
                          f"THD={m['thd_high_pct']:5.2f}% "
                          f"P={m['supply_mw']:6.1f}mW "
                          f"VCE={m['qa_vce_high_v']:.2f}V")
                    (M.RESULTS / "final_matrix.json").write_text(
                        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
