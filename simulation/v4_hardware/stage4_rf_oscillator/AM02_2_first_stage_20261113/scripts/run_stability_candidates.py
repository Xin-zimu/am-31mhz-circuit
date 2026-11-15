# -*- coding: utf-8 -*-
"""Startup and terminated-input stability check for the five candidates."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am022_lib as L

OUT = L.RESULTS / "candidate_stability.json"


def build(candidate, rterm):
    node = L.input_node(candidate)
    body = L.circuit(candidate, 10000.0).split("VCC vcc 0 DC 5\n", 1)[1].rstrip()
    term = ""
    if rterm:
        term = f"\nCTERM {node} rt 100p\nRTERM rt 0 {rterm:g}"
    return "\n".join([
        f"* AM-02.2 stability {candidate}, input termination={rterm}",
        "VCC vcc 0 PWL(0 0 1u 5)",
        body,
        term.strip(),
        L.MODEL,
        ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27",
        ".control",
        "set num_threads=1",
        "set filetype=binary",
        f"save v(out) v({node})",
        "tran 0.5n 250u 0 0.5n",
        "write @RAW@",
        "quit",
        ".endc",
        ".end",
    ]) + "\n"


def measure(raw):
    d = L.read_raw(raw)
    t = d["time"]
    mask = t >= 150e-6
    y = d[[k for k in d if k.startswith("v(") and k != "v(vcc)"][0]]
    # Explicit output vector, tolerate different variable order.
    y = d.get("v(out)", y)
    y = y[mask]
    t = t[mask]
    y = y - np.mean(y)
    rms = float(np.sqrt(np.mean(y ** 2)))
    # rectangular-window FFT is enough to detect a sustained RF oscillation
    amp = 2 * np.abs(np.fft.rfft(y)) / len(y)
    f = np.fft.rfftfreq(len(y), np.median(np.diff(t)))
    idx = int(np.argmax(amp))
    return {"output_rms_mv": 1000 * rms, "output_max_mv": 1000 * float(np.max(np.abs(y))),
            "peak_frequency_mhz": float(f[idx] / 1e6),
            "peak_amplitude_mv": 1000 * float(amp[idx])}


def main():
    records = []
    for candidate in "ABCDE":
        for rterm in (None, 1000.0):
            tag = f"stab_{candidate}_{'open' if rterm is None else int(rterm)}"
            raw = L.RAWS / (tag + ".raw")
            log = L.LOGS / (tag + ".log")
            cir = L.NETLISTS / (tag + ".cir")
            text = build(candidate, rterm).replace("@RAW@", raw.as_posix())
            cir.write_text(text, encoding="utf-8", newline="\n")
            with log.open("w", encoding="utf-8", errors="replace") as stream:
                proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                                      stdout=stream, stderr=subprocess.STDOUT, timeout=120)
            if proc.returncode != 0 or not raw.exists():
                raise RuntimeError("stability run failed " + tag)
            item = measure(raw)
            item.update(candidate=candidate, input_termination_ohm=rterm,
                        netlist=str(cir), netlist_sha256=L.sha(cir),
                        raw_sha256=L.sha(raw), log_sha256=L.sha(log))
            records.append(item)
            print(tag, item)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
