# -*- coding: utf-8 -*-
"""Run the untouched POLY(3) mathematical law with the same matrix definitions."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

AMPS = [1.0, 2.0, 3.0, 4.0]
DUTIES = [0.1, 0.3, 0.5]
LOADS = [2000.0, 10000.0]
OUT = L.RESULTS / "poly_matrix.json"
SUMMARY = L.RESULTS / "comparison_summary.json"


def build(amp, duty, load):
    width = duty * 50e-6 - 40e-9
    return f"""* Original POLY(3) modulation law: VAM=Vc*(0.6+0.1*V1)
VMOD mod 0 PULSE(0 {amp:.12g} 25u 20n 20n {width:.12g} 50u)
BAM out 0 V=(0.6+0.1*v(mod))*sin(2*pi*31e6*time)
RL out 0 {load:.12g}
CL out 0 10p
.options method=trap maxord=2 reltol=1e-5 trtol=7
.control
set filetype=binary
save v(out) v(mod)
tran 0.5n 130u 0 0.5n
write @RAW@
quit
.endc
.end
"""


def measure(raw, amp, duty, load):
    data = L.read_raw(raw)
    t = data["time"]
    env = L.demodulate(t, data["v(out)"])
    p0 = 75e-6
    high = (p0, p0 + duty * 50e-6)
    low = (p0 + duty * 50e-6, p0 + 50e-6)
    ah = L._median_plateau(t, env, *high)
    al = L._median_plateau(t, env, *low)
    step = ah - al
    mid = 0.5 * (ah + al)
    rise = L._crossing(t, env, mid, high[0], True)
    fall = L._crossing(t, env, mid, high[1], False)
    return {
        "amp_vpp": amp,
        "duty_pct": 100 * duty,
        "load_ohm": load,
        "carrier_vpp_high": 2 * ah,
        "carrier_vpp_low": 2 * al,
        "envelope_step_vpp": 2 * step,
        "modulation_index": step / (ah + al),
        "envelope_duty_pct": 100 * (fall - rise) / 50e-6,
    }


def main():
    records = []
    for load in LOADS:
        for duty in DUTIES:
            for amp in AMPS:
                tag = f"poly_rl{int(load)}_d{round(duty*100):02d}_a{amp:g}"
                cir = L.NETLISTS / (tag + ".cir")
                raw = L.RAWS / (tag + ".raw")
                log = L.LOGS / (tag + ".log")
                cir.write_text(build(amp, duty, load).replace("@RAW@", raw.as_posix()),
                               encoding="utf-8", newline="\n")
                with log.open("w", encoding="utf-8", errors="replace") as stream:
                    proc = subprocess.run([str(L.EXE), "-b", str(cir)], cwd=L.RESULTS,
                                          stdout=stream, stderr=subprocess.STDOUT, timeout=120)
                if proc.returncode != 0 or not raw.exists():
                    raise RuntimeError("POLY comparison run failed: " + tag)
                item = measure(raw, amp, duty, load)
                item["netlist"] = str(cir)
                item["netlist_sha256"] = L.sha256(cir)
                item["raw_sha256"] = L.sha256(raw)
                records.append(item)
                raw.unlink(missing_ok=True)
    output = {
        "model": "VAM=(0.6+0.1*V1)*1.0*sin(2*pi*31e6*t), identical to original POLY(3) coefficient law",
        "conditions": {"amplitudes_vpp": AMPS, "duties_pct": [100*d for d in DUTIES],
                       "loads_ohm": LOADS, "carrier": "31 MHz, 2 Vpp equivalent"},
        "records": records,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    final = json.loads((L.RESULTS / "matrix_final.json").read_text(encoding="utf-8"))
    optimized = next(r for r in final["records"] if r["load_ohm"] == 2000
                     and r["amp_vpp"] == 4 and r["duty_pct"] == 50)
    reference = next(r for r in records if r["load_ohm"] == 2000
                     and r["amp_vpp"] == 4 and r["duty_pct"] == 50)
    ratios = {}
    for key in ("carrier_vpp_high", "carrier_vpp_low", "envelope_step_vpp"):
        ratios[key] = optimized[key] / reference[key]
        ratios[key + "_db"] = 20 * np.log10(ratios[key])
    summary = {
        "reference_point": {"amp_vpp": 4, "duty_pct": 50, "load_ohm": 2000},
        "optimized": {k: optimized[k] for k in
                      ("carrier_vpp_high", "carrier_vpp_low", "envelope_step_vpp",
                       "modulation_index", "supply_power_mw")},
        "poly": {k: reference[k] for k in
                 ("carrier_vpp_high", "carrier_vpp_low", "envelope_step_vpp",
                  "modulation_index")},
        "amplitude_ratios": ratios,
    }
    summary["post_modulator_gain_needed_to_match_poly_db"] = -20 * np.log10(
        optimized["mean_carrier_vpp"] / ((reference["carrier_vpp_high"] + reference["carrier_vpp_low"]) / 2))
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Wrote", OUT, SUMMARY)


if __name__ == "__main__":
    main()
