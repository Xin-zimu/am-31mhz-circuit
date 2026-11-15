# -*- coding: utf-8 -*-
"""Preliminary AM-02.1 output-impedance audit at the two modulation plateaus.

This is a small-signal AC audit only; it does not design or add an amplifier.
The test load is removed and a 1 A AC current is injected into the output node.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
OUT = L.RESULTS / "output_impedance_31mhz.json"


def run_point(level):
    # Actual Q2 base voltages at the 4 Vpp / 50% high and low plateaus.
    bias = {"high": 1.2533955684103804, "low": 1.0294931166190022}[level]
    raw = L.RAWS / f"zout_{level}.raw"
    log = L.LOGS / f"zout_{level}.log"
    text = L.build_netlist(PARAMS, 0.0, 0.5, 2000.0, state=None,
                           carrier=True, cold=False, stop_us=1.0,
                           raw_name=raw.as_posix())
    text = text.replace("VRF src 0 SIN(0 1 31meg)", "VRF src 0 DC 0 AC 0")
    text = re.sub(r"VMOD mod 0 PULSE\([^\n]+\)", "VMOD mod 0 DC 0", text)
    text = re.sub(r"(?m)^RL out 0 .*$", "", text)
    text = re.sub(r"(?m)^CL out 0 .*$", "", text)
    text = re.sub(r"(?m)^COUT c1 out .*$",
                  lambda match: (match.group(0)
                                 + "\nVTEST out 0 DC 0 AC 1"
                                 + f"\nLB2 b2 vbias 1H\nVB2 vbias 0 DC {bias:.12g}"), text)
    start = text.index(".control")
    text = text[:start] + """.control
set num_threads=1
ac lin 1 31meg 31meg
let zout = -v(out)/i(vtest)
print mag(zout) ph(zout)
quit
.endc
.end
"""
    cir = L.NETLISTS / f"zout_{level}.cir"
    cir.write_text(text, encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("Zout run failed: " + str(log))
    body = log.read_text(encoding="utf-8", errors="replace")
    magnitude = float(re.search(r"mag\(zout\)\s*=\s*([0-9.eE+-]+)", body).group(1))
    phase = float(re.search(r"ph\(zout\)\s*=\s*([0-9.eE+-]+)", body).group(1))
    resistance = magnitude * __import__("math").cos(__import__("math").radians(phase))
    reactance = magnitude * __import__("math").sin(__import__("math").radians(phase))
    return {
        "plateau": level,
        "forced_b2_dc_v": bias,
        "magnitude_ohm": magnitude,
        "phase_deg": phase,
        "resistance_ohm": resistance,
        "reactance_ohm": reactance,
        "netlist": str(cir),
        "netlist_sha256": L.sha256(cir),
        "log_sha256": L.sha256(log),
    }


def main():
    payload = {
        "frequency_hz": 31e6,
        "method": "AC voltage injection at out; RL and CL removed; Q2 base forced to the measured high/low plateau voltage through a 1 H AC-blocking inductor",
        "caveat": "Small-signal audit around each plateau; not a large-signal load-pull measurement",
        "points": [run_point("high"), run_point("low")],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
