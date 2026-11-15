# -*- coding: utf-8 -*-
"""Run the required Q2 base-injection resistor sweep plus necessary extensions."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

VALUES_K = [82, 68, 56, 47, 39, 36, 33, 27, 22]
OUT = L.RESULTS / "rbb_sweep.json"


def main():
    records = []
    for value_k in VALUES_K:
        print(f"\nRBB={value_k} kOhm")
        metrics = L.evaluate_case({"rbb": value_k * 1e3}, 4.0, 0.5, 2000.0,
                                  f"sweep{value_k:02d}", keep_raw=False)
        records.append(metrics)
        print(f"  m={100*metrics['modulation_index']:.3f}% "
              f"high={metrics['carrier_vpp_high']:.5f} "
              f"low={metrics['carrier_vpp_low']:.5f} "
              f"step={metrics['envelope_step_vpp']:.5f} Vpp")
    target = 0.25
    eligible = [r for r in records if abs(r["modulation_index"] - target) <= 0.02]
    selection = min(eligible, key=lambda r: abs(r["modulation_index"] - target)) if eligible else None
    output = {
        "conditions": {"amp_vpp": 4.0, "duty_pct": 50.0, "load_ohm": 2000.0,
                       "carrier": "31 MHz, 2 Vpp", "method": "periodic capacitor shooting"},
        "required_values_kohm": [82, 68, 56, 47, 39],
        "extension_values_kohm": [33, 27, 22],
        "target_modulation_index": target,
        "selection": selection["rbb_ohm"] if selection else None,
        "records": records,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nSelected RBB:", output["selection"])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
