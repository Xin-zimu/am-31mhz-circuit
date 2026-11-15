# -*- coding: utf-8 -*-
"""AM-02.3 step 7: one table for every second-stage candidate.

Per topology: DC operating point (in the real cascade), small-signal gain at
31 MHz into 50 ohm || 10 pF, gain 20 kHz either side (envelope sidebands),
complex input impedance at 31 MHz and the equivalent parallel capacitance.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

CANDS = {
    "S1_EF_CE": ("S1", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                        "rb1": 100e3, "rb2": 100e3, "ref": 900.0,
                        "ltank": 1.2e-6, "ct1": 22e-12, "ct2": 68e-12}),
    "S2_CE_tank": ("S2", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                          "rea": 100.0, "ltank": 1.2e-6, "ct1": 22e-12,
                          "ct2": 68e-12}),
    "S3_CE_RFC_EF": ("S3", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                            "rea": 100.0, "lrfc": 2.2e-6, "reb": 180.0}),
    "S4_cascode": ("S4", {"rbat": 2.2e3, "rbab": 1.5e3, "rax": 5.0,
                          "rea": 100.0, "rbx1": 1e3, "rbx2": 3.9e3,
                          "ltank": 1.2e-6, "ct1": 22e-12, "ct2": 82e-12}),
    "S6_matched_CE": ("S6", {"rbat": 2.2e3, "rbab": 1.1e3, "rax": 8.0,
                             "rea": 39.0, "lm": 0.82e-6, "cm": 68e-12,
                             "rser": 10.0, "ltank": 0.47e-6,
                             "ct1": 100e-12, "ct2": 56e-12}),
}


def main():
    rows = []
    for label, (top, stage) in CANDS.items():
        name = f"tab_{top}"
        M.run(name, M.standalone(top, stage, mode="ac", raw_name=name + ".raw"))
        m, _, _ = M.ac_metrics(M.RESULTS / (name + ".raw"))
        op = M.op_state(top, stage, tag=f"tab_op_{top}")
        n = op["nodes"]
        ic = (5.0 - n.get("ca", 5.0)) / 1.0
        row = {
            "config": label,
            "topology": top,
            "gain_31_db": round(m["gain_db"], 2),
            "gain_31m20k_db": round(m["gain_at_minus20k_db"], 2),
            "gain_31p20k_db": round(m["gain_at_plus20k_db"], 2),
            "f_peak_mhz": round(m["f_peak_mhz"], 2),
            "zin_real": round(m["zin_real"], 1),
            "zin_imag": round(m["zin_imag"], 1),
            "zin_equiv_pf": None if m["zin_equiv_pf"] is None else round(m["zin_equiv_pf"], 1),
            "v_ca_dc": round(n.get("ca", n.get("ca_a", 0.0)), 3),
            "v_e_dc": round(n.get("ea", n.get("ea_a", 0.0)), 3),
            "vce_v": round(n.get("ca", n.get("ca_a", 0.0)) - n.get("ea", n.get("ea_a", 0.0)), 3),
        }
        rows.append(row)
        print(f"{label:<16} G={row['gain_31_db']:6.2f} dB  "
              f"Zin={row['zin_real']:7.1f}{row['zin_imag']:+8.1f}j  "
              f"({row['zin_equiv_pf']} pF)  fpk={row['f_peak_mhz']:.1f} MHz  "
              f"VCE={row['vce_v']:.2f} V")

    out = M.RESULTS / "topology_table.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = M.ROOT / "AM02_3_topology_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", out, csv_path)


if __name__ == "__main__":
    main()
