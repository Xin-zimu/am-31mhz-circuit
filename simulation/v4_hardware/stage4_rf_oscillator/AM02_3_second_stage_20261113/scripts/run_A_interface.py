# -*- coding: utf-8 -*-
"""AM-02.3 step 2: the real output interface of AM-02.2 scheme A.

AM-02.2 shipped scheme A with a 10 kOhm / 2 kOhm load only. The second stage
needs the loaded interface, so this run repeats the A cascade against a set of
real loads and extracts the source resistance from the measured envelope, with
no impedance model in between.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

LOADS = [50.0, 100.0, 200.0, 470.0, 1000.0, 2000.0, 4700.0, 10000.0]
OUT = M.RESULTS / "schemeA_interface.json"


def main():
    rows = []
    for rl in LOADS:
        stage = {"rload": rl}
        print(f"A output into {rl:g} ohm")
        solve = M.solve_cap("SA", stage, 4.0, 0.5, tag=f"a{int(rl)}")
        state = dict(solve["op"]["nodes"])
        state["b2ac"] = -2.0 + solve["vcap"]   # capacitor voltage, mod low = -2 V
        name = f"a_if{int(rl)}"
        M.run(name, M.build("SA", stage, 4.0, 0.5, state=state, stop_us=128.0,
                            raw_name=name + ".raw"))
        m = M.measure(M.RESULTS / (name + ".raw"), "SA", 0.5, p0_us=75.0,
                      load_r=rl)
        m["cap_v"] = solve["vcap"]
        m["cap_residual_mv"] = 1e3 * solve["residual"]
        rows.append(m)
        print(f"  high {m['vpp_high']*1e3:.2f} mVpp  low {m['vpp_low']*1e3:.2f} mVpp "
              f"m={100*m['modulation_index']:.2f}%  P={m['supply_mw']:.2f} mW")

    ref = [r for r in rows if abs(r["load_ohm"] - 10000.0) < 1][0]
    for r in rows:
        r["loss_vs_10k_db"] = 20 * math.log10(r["vpp_high"] / ref["vpp_high"])

    # two-point source resistance from the 2 k / 10 k pair (model: real R_s)
    a = next(r for r in rows if r["load_ohm"] == 2000.0)
    b = ref
    # V = K*R/(R+Rs) with R1=2k, R2=10k, u=V1/V2  ->  Rs = 2000*(1-u)/(u-0.2)
    u = a["vpp_high"] / b["vpp_high"]
    rs = 2000.0 * (1.0 - u) / (u - 0.2)
    summary = {"loads": LOADS, "rows": rows, "rs_two_point_ohm": rs,
               "v_open_high_vpp": ref["vpp_high"] * (10000.0 + rs) / 10000.0}
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"two-point Rs = {rs:.1f} ohm, open-circuit high = "
          f"{summary['v_open_high_vpp']*1e3:.2f} mVpp")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
