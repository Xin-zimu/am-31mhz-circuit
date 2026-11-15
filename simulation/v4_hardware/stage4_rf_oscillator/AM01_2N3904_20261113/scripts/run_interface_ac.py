# -*- coding: utf-8 -*-
"""Small-signal input impedance at 31 MHz for baseline and final interfaces."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

CASES = {
    "baseline_10k_100": {"rbb": 82e3, "re": 470.0, "rin": 10e3, "rsh": 100.0, "cin": 100e-12},
    "final_2k2_10": {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9},
}
OUT = L.RESULTS / "interface_ac.json"


def main():
    records = {}
    for name, params in CASES.items():
        text = L.build_netlist(params, 0.0, 0.5, 2000.0, state=None,
                               carrier=True, cold=False)
        text = text.replace("VRF src 0 SIN(0 1 31meg)", "VRF src 0 DC 0 AC 1")
        text = re.sub(r"VMOD mod 0 PULSE\([^\n]+\)", "VMOD mod 0 DC 0", text)
        start = text.index(".control")
        text = text[:start] + """.control
set num_threads=1
ac lin 1 31meg 31meg
let zin = v(src)/(-i(vrf))
print mag(zin) ph(zin)
quit
.endc
.end
"""
        cir = L.NETLISTS / f"interface_{name}.cir"
        log = L.LOGS / f"interface_{name}.log"
        cir.write_text(text, encoding="utf-8", newline="\n")
        with log.open("w", encoding="utf-8", errors="replace") as stream:
            proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError("AC run failed " + str(log))
        body = log.read_text(encoding="utf-8", errors="replace")
        magnitude = re.search(r"mag\(zin\)\s*=\s*([0-9.eE+-]+)", body)
        phase = re.search(r"ph\(zin\)\s*=\s*([0-9.eE+-]+)", body)
        if not magnitude or not phase:
            raise RuntimeError("Could not parse impedance from " + str(log))
        records[name] = {
            "params": params,
            "magnitude_ohm": float(magnitude.group(1)),
            "phase_deg": float(phase.group(1)),
            "netlist": str(cir),
            "log": str(log),
            "netlist_sha256": L.sha256(cir),
        }
        print(name, records[name]["magnitude_ohm"], records[name]["phase_deg"])
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
