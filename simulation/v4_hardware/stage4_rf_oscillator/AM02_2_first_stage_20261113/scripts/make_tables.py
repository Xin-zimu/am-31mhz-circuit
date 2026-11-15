# -*- coding: utf-8 -*-
"""Export AM-02.2 candidate and cascade summary CSV files."""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    candidates = json.loads((RES / "candidates.json").read_text(encoding="utf-8"))
    rows = []
    for candidate in candidates["candidates"]:
        for load in candidate["loads"]:
            response = load["response"]
            rows.append({
                "candidate": candidate["candidate"],
                "description": candidate["description"],
                "load_ohm": load["load_ohm"],
                "zin_real_ohm": load["zin_real_ohm"],
                "zin_imag_ohm": load["zin_imag_ohm"],
                "zin_mag_ohm": load["zin_mag_ohm"],
                "zin_phase_deg": load["zin_phase_deg"],
                "parallel_c_pf": load["parallel_c_pf"],
                "vce_q1": load["vce"].get("q1") if isinstance(load["vce"], dict) else load["vce"],
                "vce_q2": load["vce"].get("q2") if isinstance(load["vce"], dict) else "",
                "supply_current_ma": load["dc"]["supply_current_ma"],
                "supply_power_mw": load["dc"]["supply_power_mw"],
                "gain_1mhz_db": response["gain_1mhz_db"],
                "gain_25mhz_db": response["gain_25mhz_db"],
                "gain_31mhz_db": response["gain_31mhz_db"],
                "gain_37mhz_db": response["gain_37mhz_db"],
                "phase_31mhz_deg": response["phase_31mhz_deg"],
                "minus3db_frequency_mhz": response["minus3db_frequency_mhz"],
                "peak_gain_db": response["peak_gain_db"],
                "peak_frequency_mhz": response["peak_frequency_mhz"],
            })
    write(ROOT / "AM02_2_candidates.csv",
          ["candidate", "description", "load_ohm", "zin_real_ohm", "zin_imag_ohm",
           "zin_mag_ohm", "zin_phase_deg", "parallel_c_pf", "vce_q1", "vce_q2",
           "supply_current_ma", "supply_power_mw", "gain_1mhz_db",
           "gain_25mhz_db", "gain_31mhz_db", "gain_37mhz_db", "phase_31mhz_deg",
           "minus3db_frequency_mhz", "peak_gain_db", "peak_frequency_mhz"], rows)

    cascade = json.loads((RES / "cascade_loading.json").read_text(encoding="utf-8"))
    crow = []
    for r in cascade:
        a = (r["am01_out"]["high_vpp"] + r["am01_out"]["low_vpp"]) / 2
        c = (r["candidate_out"]["high_vpp"] + r["candidate_out"]["low_vpp"]) / 2
        total = 20 * math.log10(1.6 / a)
        first = 20 * math.log10(c / a)
        second = 20 * math.log10(1.6 / c)
        crow.append({
            "candidate": r["candidate"], "load_ohm": r["load_ohm"],
            "am01_high_vpp": r["am01_out"]["high_vpp"],
            "am01_low_vpp": r["am01_out"]["low_vpp"],
            "am01_mean_vpp": a,
            "am01_modulation_index": r["am01_out"]["modulation_index"],
            "candidate_high_vpp": r["candidate_out"]["high_vpp"],
            "candidate_low_vpp": r["candidate_out"]["low_vpp"],
            "candidate_mean_vpp": c,
            "first_stage_gain_db": first,
            "total_gain_to_1p6_db": total,
            "second_stage_needed_db": second,
            "loading_penalty_db": total - 30.31,
        })
    write(ROOT / "AM02_2_cascade.csv",
          ["candidate", "load_ohm", "am01_high_vpp", "am01_low_vpp",
           "am01_mean_vpp", "am01_modulation_index", "candidate_high_vpp",
           "candidate_low_vpp", "candidate_mean_vpp", "first_stage_gain_db",
           "total_gain_to_1p6_db", "second_stage_needed_db", "loading_penalty_db"], crow)
    print("Wrote AM02_2_candidates.csv and AM02_2_cascade.csv")


if __name__ == "__main__":
    main()
