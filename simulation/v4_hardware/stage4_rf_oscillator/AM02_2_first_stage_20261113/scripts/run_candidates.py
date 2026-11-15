# -*- coding: utf-8 -*-
"""Official AM-02.2 candidate table: DC, Zin, gain and response."""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am022_lib as L

OUT = L.RESULTS / "candidates.json"
DESCRIPTIONS = {
    "A": "2N3904 common emitter, unbypassed RE=100 ohm",
    "B": "2N3904 common base, base AC-grounded",
    "C": "A followed by emitter follower Q2",
    "D": "2N3904 cascode: Q1 CE with RF-bypassed RE + Q2 CB",
    "E": "Emitter-follower input Q1 followed by CE Q2",
}


def number(pattern, text, default=float("nan")):
    match = re.search(pattern, text)
    return float(match.group(1)) if match else default


def parse_dc(log):
    text = Path(log).read_text(encoding="utf-8", errors="replace")
    nodes = {}
    for match in re.finditer(r"(?m)^v\(([^)]+)\)\s*=\s*([0-9.eE+-]+)", text):
        nodes[match.group(1)] = float(match.group(2))
    currents = {}
    for match in re.finditer(r"(?m)^@(q\d+)\[(ic|ib)\]\s*=\s*([0-9.eE+-]+)", text):
        currents[f"{match.group(1)}_{match.group(2)}"] = float(match.group(3))
    supply = abs(number(r"i\(vcc\)\s*=\s*([0-9.eE+-]+)", text, 0.0))
    return {"nodes": nodes, "currents": currents,
            "supply_current_ma": 1000 * supply,
            "supply_power_mw": 5000 * supply}


def vce(candidate, nodes):
    if candidate in ("A", "B"):
        return nodes["c"] - nodes["e"]
    if candidate == "C":
        return {"q1": nodes["c"] - nodes["e"], "q2": 5.0 - nodes["e2"]}
    if candidate == "D":
        return {"q1": nodes["x"] - nodes["e"], "q2": nodes["c2"] - nodes["x"]}
    if candidate == "E":
        return {"q1": 5.0 - nodes["e1"], "q2": nodes["c2"] - nodes["e2"]}
    raise ValueError(candidate)


def response_metrics(record):
    f = np.asarray(record["response_frequency_mhz"])
    g = np.asarray(record["response_gain_db"])
    p = np.asarray(record["response_phase_deg"])

    def at(x):
        i = int(np.argmin(np.abs(f - x)))
        return float(g[i]), float(p[i])

    g25, p25 = at(25)
    g31, p31 = at(31)
    g37, p37 = at(37)
    g1, p1 = at(1)
    gain_drop_31_vs_1 = g31 - g1
    # -3 dB point relative to the 1 MHz gain only where it actually rolls off.
    candidates = np.where((f > 1) & (g <= g1 - 3.0))[0]
    f3 = float(f[candidates[0]]) if candidates.size else None
    return {"gain_1mhz_db": g1, "gain_25mhz_db": g25, "gain_31mhz_db": g31,
            "gain_37mhz_db": g37, "phase_31mhz_deg": p31,
            "gain_31_vs_1_db": gain_drop_31_vs_1,
            "minus3db_frequency_mhz": f3,
            "peak_gain_db": float(np.max(g)), "peak_frequency_mhz": float(f[np.argmax(g)]),
            "response_ripple_db_1_100": float(np.max(g) - np.min(g))}


def main():
    records = []
    for candidate in "ABCDE":
        print("candidate", candidate)
        load_records = []
        for load in (2000.0, 10000.0):
            gainrec = L.run(candidate, load)
            zinrec = L.run_zin(candidate, load)
            dc = parse_dc(gainrec["log"])
            item = {
                "load_ohm": load,
                "dc": dc,
                "vce": vce(candidate, dc["nodes"]),
                "zin_real_ohm": zinrec["zin_real_ohm"],
                "zin_imag_ohm": zinrec["zin_imag_ohm"],
                "zin_mag_ohm": zinrec["zin_mag_ohm"],
                "zin_phase_deg": zinrec["zin_phase_deg"],
                "parallel_c_pf": zinrec["parallel_c_pf"],
                "response": response_metrics(gainrec),
                "gain_netlist": gainrec["netlist"],
                "zin_netlist": zinrec["netlist"],
                "gain_netlist_sha256": gainrec["netlist_sha256"],
                "zin_netlist_sha256": zinrec["netlist_sha256"],
            }
            load_records.append(item)
            print(" ", int(load), "Zin", round(item["zin_mag_ohm"], 1),
                  "C", round(item["parallel_c_pf"], 2),
                  "G31", round(item["response"]["gain_31mhz_db"], 2))
        records.append({
            "candidate": candidate,
            "description": DESCRIPTIONS[candidate],
            "input_node": L.input_node(candidate),
            "output_node": L.candidate_out(candidate),
            "loads": load_records,
        })
    OUT.write_text(json.dumps({"candidates": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
