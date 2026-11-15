# -*- coding: utf-8 -*-
"""Record the 4 Vpp / 50% / 50 ohm termination point with explicit definitions."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
OUT = L.RESULTS / "termination_50ohm.json"


def main():
    result = L.evaluate_case(PARAMS, 4.0, 0.5, 50.0, "termination50",
                             keep_raw=False, verbose=False)
    mean_high_low = 0.5 * (result["carrier_vpp_high"] + result["carrier_vpp_low"])
    payload = {
        "point": {"amp_vpp": 4.0, "duty_pct": 50.0, "load_ohm": 50.0,
                  "carrier": "31 MHz, 2 Vpp equivalent at TP2 interface"},
        "definitions": {
            "carrier_vpp_high": "median carrier Vpp on the central 60% of the high envelope plateau",
            "carrier_vpp_low": "median carrier Vpp on the central 60% of the low envelope plateau",
            "mean_carrier_vpp": "2 * time average of the demodulated carrier peak envelope over one complete 20 kHz period",
            "at_50pct_duty": "mean_carrier_vpp equals the arithmetic mean of high and low plateau Vpp",
        },
        "carrier_vpp_high": result["carrier_vpp_high"],
        "carrier_vpp_low": result["carrier_vpp_low"],
        "mean_carrier_vpp": result["mean_carrier_vpp"],
        "arithmetic_mean_high_low_vpp": mean_high_low,
        "modulation_index": result["modulation_index"],
        "envelope_duty_pct": result["envelope_duty_pct"],
        "q1_vce_high_v": result["q1_vce_high_v"],
        "q1_vce_low_v": result["q1_vce_low_v"],
        "q2_vce_high_v": result["q2_vce_high_v"],
        "q2_vce_low_v": result["q2_vce_low_v"],
        "supply_power_mw": result["supply_power_mw"],
        "netlist": result["cir"],
        "netlist_sha256": result["cir_sha256"],
        "raw_sha256": result["raw_sha256"],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
