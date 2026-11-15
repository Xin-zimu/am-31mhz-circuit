# -*- coding: utf-8 -*-
"""Carrier-off and unmodulated-carrier spectral stability checks."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
OUT = L.RESULTS / "stability.json"


def spectrum(t, y, start=75e-6, stop=125e-6):
    mask = (t >= start) & (t <= stop)
    ts = t[mask]
    ys = y[mask] - np.mean(y[mask])
    if not np.allclose(np.diff(ts), np.diff(ts)[0], rtol=1e-6, atol=1e-15):
        ts = np.linspace(start, stop, 100001)
        ys = np.interp(ts, t, y)
        ys -= np.mean(ys)
    w = np.hanning(len(ys))
    amplitude = 2.0 * np.abs(np.fft.rfft(ys * w)) / np.sum(w)
    frequency = np.fft.rfftfreq(len(ys), ts[1] - ts[0])
    return frequency, amplitude


def spurious(frequency, amplitude, carrier_present):
    mask = frequency >= 5e6
    if carrier_present:
        exclude = np.zeros_like(frequency, dtype=bool)
        for harmonic in (31e6, 62e6, 93e6, 124e6, 155e6, 186e6):
            exclude |= np.abs(frequency - harmonic) <= 1e6
        mask &= ~exclude
    index = np.argmax(amplitude[mask])
    return {
        "max_spurious_frequency_mhz": float(frequency[mask][index] / 1e6),
        "max_spurious_amplitude_mv": 1000.0 * float(amplitude[mask][index]),
        "spurious_rms_5mhz_plus_mv": 1000.0 * float(
            np.sqrt(np.sum(amplitude[mask] ** 2))),
    }


def run(solve, carrier, label):
    amp = 4.0
    duty = 0.5
    low = -amp * duty
    state = L.base_state(solve["vcap"], low)
    info = L.run(PARAMS, amp, duty, 2000.0, state=state, carrier=carrier,
                 stop_us=130.0, tag=label)
    data = L.read_raw(info["raw"])
    frequency, amplitude = spectrum(data["time"], data["v(out)"])
    carrier_amp = float(np.interp(31e6, frequency, amplitude)) if carrier else 0.0
    result = {
        "label": label,
        "carrier_enabled": carrier,
        "carrier_31mhz_vpp": 2.0 * carrier_amp,
        "rf_rms_5mhz_plus_mv": 1000.0 * float(
            np.sqrt(np.sum(amplitude[frequency >= 5e6] ** 2))),
        "netlist": info["cir"],
        "netlist_sha256": info["cir_sha256"],
        "raw_sha256": info["raw_sha256"],
    }
    result.update(spurious(frequency, amplitude, carrier))
    if carrier_amp:
        result["max_spurious_dbc"] = 20.0 * np.log10(
            max(result["max_spurious_amplitude_mv"], 1e-12)
            / max(1000.0 * carrier_amp, 1e-12))
    Path(info["raw"]).unlink(missing_ok=True)
    return result


def main():
    solve = L.periodic_cap_solve(PARAMS, 4.0, 0.5, 2000.0, "stab", verbose=False)
    records = [
        run(solve, False, "stability_no_carrier"),
        run(solve, True, "stability_no_modulation"),
    ]
    output = {"conditions": "A=4 Vpp, 50%, RL=2k, final component values",
              "records": records}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    for record in records:
        print(record)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
