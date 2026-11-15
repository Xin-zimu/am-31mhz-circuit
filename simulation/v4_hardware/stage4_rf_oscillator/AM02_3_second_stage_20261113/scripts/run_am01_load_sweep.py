# -*- coding: utf-8 -*-
"""AM-02.3 step 1: direct AM-01 load sweep.

The AM-01 output impedance was previously reported as a complex number, and the
two-point arithmetic used earlier disagreed with it. AM-02.3 therefore does not
use any impedance model at all: it measures the frozen modulator's high/low
envelope directly against a set of real loads, and the second stage is designed
against that curve. This is the same discipline the review already adopted when
the 369 ohm extrapolation was withdrawn.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

LOADS = [50.0, 100.0, 220.0, 470.0, 1000.0, 2200.0, 4700.0, 10000.0]
P = M.AM01_P
OUT = M.RESULTS / "am01_load_sweep.json"


def main():
    rows = []
    for rl in LOADS:
        print(f"AM-01 into {rl:g} ohm")
        solve = M.L.periodic_cap_solve(P, 4.0, 0.5, rl, f"ld{rl:g}".replace(".", "p"),
                                       verbose=True)
        state = M.L.base_state(solve["vcap"], -2.0)
        info = M.L.run(P, 4.0, 0.5, rl, state=state, stop_us=108.0,
                       tag=f"ld{rl:g}".replace(".", "p"))
        m = M.L.measure(info, p0_us=55.0)
        m["cap_v"] = solve["vcap"]
        m["cap_residual_mv"] = 1000.0 * solve["residual_v"]
        m["cir_sha256"] = info["cir_sha256"]
        Path(info["raw"]).unlink(missing_ok=True)
        m["raw"] = None
        rows.append(m)
        print(f"  high {m['carrier_vpp_high']*1e3:.3f} mVpp  "
              f"low {m['carrier_vpp_low']*1e3:.3f} mVpp  "
              f"m={100*m['modulation_index']:.2f}%  "
              f"P={m['supply_power_mw']:.2f} mW")
        OUT.write_text(json.dumps({"loads": LOADS, "rows": rows}, indent=2,
                                  ensure_ascii=False), encoding="utf-8")

    # decay from the 10 kOhm reference: how much level each load costs
    ref = next(r for r in rows if r["load_ohm"] == 10000.0)
    for r in rows:
        r["loss_vs_10k_db"] = 20 * __import__("math").log10(
            r["carrier_vpp_high"] / ref["carrier_vpp_high"])
    OUT.write_text(json.dumps({"loads": LOADS, "rows": rows}, indent=2,
                              ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
