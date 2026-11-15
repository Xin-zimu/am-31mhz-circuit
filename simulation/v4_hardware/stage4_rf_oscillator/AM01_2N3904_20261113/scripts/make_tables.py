# -*- coding: utf-8 -*-
"""Export compact CSV tables from the verified JSON evidence."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    matrix = json.loads((RES / "matrix_final.json").read_text(encoding="utf-8"))
    fields = ["load_ohm", "duty_pct", "amp_vpp", "carrier_vpp_high", "carrier_vpp_low",
              "envelope_step_vpp", "modulation_index", "envelope_duty_pct",
              "rise_10_90_us", "fall_90_10_us", "carrier_thd_high", "carrier_thd_low",
              "q1_ic_high_ma", "q1_ic_low_ma", "q2_ie_high_ma", "q2_ie_low_ma",
              "q1_vce_high_v", "q1_vce_low_v", "q2_vce_high_v", "q2_vce_low_v",
              "supply_power_mw", "final_coupling_residual_mv",
              "period_to_period_high_pct", "period_to_period_low_pct"]
    write_csv(ROOT / "AM01_test_matrix.csv", fields, matrix["records"])

    sweep_rows = []
    for label, filename in [("baseline interface", "rbb_sweep_baseline_interface.json"),
                            ("final interface", "rbb_sweep_final_interface.json")]:
        data = json.loads((RES / filename).read_text(encoding="utf-8"))
        for item in data["records"]:
            sweep_rows.append({
                "interface": label,
                "rbb_ohm": item["rbb_ohm"],
                "carrier_vpp_high": item["carrier_vpp_high"],
                "carrier_vpp_low": item["carrier_vpp_low"],
                "envelope_step_vpp": item["envelope_step_vpp"],
                "modulation_index": item["modulation_index"],
                "q1_vce_high_v": item["q1_vce_high_v"],
                "q1_vce_low_v": item["q1_vce_low_v"],
                "q2_vce_high_v": item["q2_vce_high_v"],
                "q2_vce_low_v": item["q2_vce_low_v"],
            })
    write_csv(ROOT / "AM01_rbb_sweep.csv",
              ["interface", "rbb_ohm", "carrier_vpp_high", "carrier_vpp_low",
               "envelope_step_vpp", "modulation_index", "q1_vce_high_v",
               "q1_vce_low_v", "q2_vce_high_v", "q2_vce_low_v"], sweep_rows)

    poly = json.loads((RES / "poly_matrix.json").read_text(encoding="utf-8"))
    compare = []
    for opt in matrix["records"]:
        ref = next(p for p in poly["records"]
                   if p["load_ohm"] == opt["load_ohm"]
                   and abs(p["duty_pct"] - opt["duty_pct"]) < 1e-9
                   and p["amp_vpp"] == opt["amp_vpp"])
        compare.append({
            "load_ohm": opt["load_ohm"],
            "duty_pct": opt["duty_pct"],
            "amp_vpp": opt["amp_vpp"],
            "opt_high": opt["carrier_vpp_high"],
            "opt_low": opt["carrier_vpp_low"],
            "opt_step": opt["envelope_step_vpp"],
            "opt_m": opt["modulation_index"],
            "poly_high": ref["carrier_vpp_high"],
            "poly_low": ref["carrier_vpp_low"],
            "poly_step": ref["envelope_step_vpp"],
            "poly_m": ref["modulation_index"],
            "step_ratio": opt["envelope_step_vpp"] / ref["envelope_step_vpp"],
            "step_ratio_db": 20 * __import__("math").log10(
                opt["envelope_step_vpp"] / ref["envelope_step_vpp"]),
        })
    write_csv(ROOT / "AM01_vs_POLY.csv",
              ["load_ohm", "duty_pct", "amp_vpp", "opt_high", "opt_low", "opt_step",
               "opt_m", "poly_high", "poly_low", "poly_step", "poly_m",
               "step_ratio", "step_ratio_db"], compare)
    print("CSV tables written")


if __name__ == "__main__":
    main()
