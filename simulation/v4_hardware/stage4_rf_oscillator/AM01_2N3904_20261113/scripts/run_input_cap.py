# -*- coding: utf-8 -*-
"""Input-capacitance sensitivity for a 10 kOhm AM-02 first-stage load."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
OUT = L.RESULTS / "input_cap_sensitivity.json"


def main():
    rows = []
    for cap_pf in (2.0, 5.0, 8.0, 10.0):
        p = dict(PARAMS, cload=cap_pf * 1e-12)
        result = L.evaluate_case(p, 4.0, 0.5, 10000.0,
                                 f"cin{cap_pf:g}p", keep_raw=False, verbose=False)
        rows.append({
            "input_resistance_ohm": 10000.0,
            "input_capacitance_pf": cap_pf,
            "carrier_vpp_high": result["carrier_vpp_high"],
            "carrier_vpp_low": result["carrier_vpp_low"],
            "mean_carrier_vpp": result["mean_carrier_vpp"],
            "gain_to_high_2v_db": 20 * math.log10(2.0 / result["carrier_vpp_high"]),
            "gain_to_low_1p2v_db": 20 * math.log10(1.2 / result["carrier_vpp_low"]),
            "gain_to_mean_1p6v_db": 20 * math.log10(1.6 / result["mean_carrier_vpp"]),
        })
    payload = {
        "conditions": "4 Vpp, 50%, 10 kOhm in parallel with indicated capacitance",
        "purpose": "preliminary AM-02.1 input-interface sensitivity; not an amplifier design",
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
