# -*- coding: utf-8 -*-
"""Connect each first-stage candidate directly to the frozen AM-01 output.

AM-01 already has a 100 pF output DC block, so the candidate input bias can
set the DC level on its side of that capacitor. A 0 V join source is used only
as an ideal wire for the transient test.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import am022_lib as L

AM01 = HERE.parents[1] / "AM01_2N3904_20261113"
sys.path.insert(0, str(AM01 / "scripts"))
import am01_lib as A

OUT = L.RESULTS / "cascade_loading.json"
LOCAL = {
    "A": {"b": "ab", "c": "ac", "e": "ae"},
    "B": {"b": "ab", "c": "ac", "e": "ae"},
    "C": {"b": "ab", "c": "ac", "e": "ae", "e2": "ae2"},
    "D": {"b": "ab", "e": "ae", "b2": "ab2", "x": "ax", "c2": "cd"},
    "E": {"b1": "ab1", "e1": "ae1", "b2": "ab2", "c2": "cc", "e2": "ae2"},
}
DC = {
    "A": {"ab": 0.8026162, "ac": 3.700086, "ae": 0.1309076},
    "B": {"ab": 2.439076, "ac": 3.253379, "ae": 1.758806},
    "C": {"ab": 0.8026126, "ac": 3.690425, "ae": 0.1309018, "ae2": 3.016938},
    "D": {"ab": 1.108539, "ae": 0.444635, "ab2": 2.465251, "ax": 1.801860, "cd": 4.067987},
    "E": {"ab1": 2.229350, "ae1": 1.573503, "ab2": 0.8026162, "cc": 3.700086, "ae2": 0.1309076},
}


def rename(text, mapping):
    for old in sorted(mapping, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(old)}\b", mapping[old], text)
    return text


def build(candidate, load):
    matrix = json.loads((AM01 / "results" / "matrix_final.json").read_text(encoding="utf-8"))
    rec = next(r for r in matrix["records"] if r["load_ohm"] == 2000
               and r["amp_vpp"] == 4 and r["duty_pct"] == 50)
    state = A.base_state(rec["cap_solution"]["vcap"], -2.0)
    # Rebuild AM-01 then remove its test load; candidate becomes the load.
    text = A.build_netlist({"rbb": 62e3, "re": 1200, "rin": 2200, "rsh": 10, "cin": 1e-9},
                           4.0, 0.5, 2000.0, state=state, stop_us=130.0,
                           tmax_ns=0.5, raw_name="cascade.raw")
    text = re.sub(r"(?m)^RL out 0 .*$", "", text)
    text = re.sub(r"(?m)^CL out 0 .*$", "", text)
    # Candidate body with a local node namespace; out -> aout.
    body = L.circuit(candidate, load).split("VCC vcc 0 DC 5\n", 1)[1]
    mapping = dict(LOCAL[candidate])
    mapping["out"] = "aout"
    body = rename(body, mapping)
    # Prefix candidate element names so Q1/R1 etc do not collide with AM-01.
    lines = []
    for line in body.splitlines():
        match = re.match(r"^(\S+)(\s+.*)$", line)
        if match and not match.group(1).startswith((".", "*", "+")):
            line = match.group(1)[0] + "X" + candidate + "_" + match.group(1)[1:] + match.group(2)
        lines.append(line)
    body = "\n".join(lines)
    node = mapping[L.input_node(candidate)]
    candidate_out = mapping[L.candidate_out(candidate)]
    join = f"VJOIN out {node} 0"
    # Add candidate DC initial values to the AM-01 .ic line.
    ic_add = " ".join(f"v({n})={v:.10g}" for n, v in DC[candidate].items())
    text = text.replace("v(out)=0", f"v(out)={DC[candidate][node]:.10g} " + ic_add)
    # Update AM-01 transient output path to a separate file only if needed: keep
    # all relevant vectors and save both source and candidate output.
    text = text.replace("save v(src) v(rfatt) v(b1) v(c1) v(x) v(b2) v(e2) v(mod) v(b2ac) v(out) i(vsup)",
                        "save v(out) v(aout) v(mod) v(b2ac)")
    text = text.replace("write ", f"{join}\n{body}\nwrite ", 1) if False else text
    # Insert candidate before .ic so all nodes exist before initialization.
    marker = "\n.ic "
    text = text.replace(marker, "\n" + join + "\n" + body + marker, 1)
    return text


def envelope(t, y):
    env = A.demodulate(t, y)
    p0 = 75e-6
    high = (p0, p0 + 25e-6)
    low = (100e-6, 125e-6)
    ah = A._median_plateau(t, env, *high)
    al = A._median_plateau(t, env, *low)
    return {"high_vpp": 2 * ah, "low_vpp": 2 * al,
            "step_vpp": 2 * (ah - al),
            "modulation_index": (ah - al) / (ah + al) if (ah + al) else None}


def main():
    records = []
    for candidate in "ABCDE":
        for load in (2000.0, 10000.0):
            tag = f"cascade_{candidate}_{int(load)}"
            raw = L.RAWS / (tag + ".raw")
            log = L.LOGS / (tag + ".log")
            cir = L.NETLISTS / (tag + ".cir")
            text = build(candidate, load).replace("cascade.raw", raw.as_posix())
            cir.write_text(text, encoding="utf-8", newline="\n")
            with log.open("w", encoding="utf-8", errors="replace") as stream:
                proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                                      stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            if proc.returncode != 0 or not raw.exists():
                raise RuntimeError("cascade failed: " + tag + "; " + str(log))
            d = L.read_raw(raw)
            t = d["time"]
            out = envelope(t, d["v(out)"])
            amp = envelope(t, d["v(aout)"])
            item = {"candidate": candidate, "load_ohm": load,
                    "am01_out": out, "candidate_out": amp,
                    "candidate_gain_db": 20 * np.log10(amp["step_vpp"] / out["step_vpp"]),
                    "netlist": str(cir), "netlist_sha256": L.sha(cir),
                    "raw_sha256": L.sha(raw), "log_sha256": L.sha(log)}
            records.append(item)
            print(tag, "AM01 m", round(100 * out["modulation_index"], 2),
                  "out step", round(amp["step_vpp"], 5),
                  "gain", round(item["candidate_gain_db"], 2))
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
