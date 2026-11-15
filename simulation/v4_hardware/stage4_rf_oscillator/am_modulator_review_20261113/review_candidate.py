# -*- coding: utf-8 -*-
"""Reproduce and measure the proposed two-2N3904 AM modulator.

The modulation source uses the zero-mean steady-state equivalent of a 0..A V
square wave after AC coupling: high=A*(1-duty), low=-A*duty. This avoids
mistaking the roughly 8 ms input-coupling startup transient for steady AM.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import time

import numpy as np
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
EXE = Path("D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe")
MODEL = """.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)"""


def read_raw(path):
    blob = Path(path).read_bytes()
    marker = b"Binary:\n"
    end = blob.find(marker)
    if end < 0:
        raise ValueError("Only binary ngspice raw files are supported")
    head = blob[:end].decode("latin-1").replace("\r", "")
    nvar = int(re.search(r"No\. Variables:\s+(\d+)", head).group(1))
    npt = int(re.search(r"No\. Points:\s+(\d+)", head).group(1))
    names = re.findall(r"(?m)^\s*\d+\s+(\S+)\s+(?:voltage|current|time)\s*$", head)
    if len(names) != nvar:
        raise ValueError("raw variable count mismatch")
    start = end + len(marker)
    arr = np.frombuffer(blob[start:start + npt * nvar * 8], dtype=np.float64)
    arr = arr.reshape(npt, nvar)
    return {name: np.ascontiguousarray(arr[:, i]) for i, name in enumerate(names)}


def netlist(amp, duty, rload="2k", tmax="0.5n"):
    high = amp * (1.0 - duty)
    low = -amp * duty
    width = duty * 50e-6 - 40e-9
    if width <= 0:
        raise ValueError("Pulse width must exceed edge times")
    return f"""* Review candidate: A={amp:g} Vpp, D={duty:g}, RL={rload}
VSUP vcc 0 DC 5
CDEC1 vcc 0 100n
CDEC2 vcc 0 10u
VRF src 0 SIN(0 1 31meg)
RIN src rfatt 10k
RSH rfatt 0 100
CIN rfatt b1 100p
RB1T vcc b1 10k
RB1B b1 0 10k
Q1 c1 b1 x 2N3904
RC vcc c1 1k
CE1 x 0 1n
Q2 x b2 e2 2N3904
RB2T vcc b2 22k
RB2B b2 0 6.8k
RE e2 0 470
CB2 b2 0 47p
VMOD mod 0 PULSE({low:.12g} {high:.12g} 0 20n 20n {width:.12g} 50u)
CBB mod b2ac 100n
RBB b2ac b2 82k
COUT c1 out 100p
RL out 0 {rload}
CL out 0 10p
* Initialized near the periodic AC-coupled state; average condition is checked separately.
.ic v(vcc)=5 v(src)=0 v(rfatt)=0 v(b1)=2.463100 v(c1)=4.002394 v(x)=1.797899
+ v(b2)=1.141575 v(e2)=0.4758707 v(mod)={low:.12g} v(b2ac)={1.141575 + low:.12g} v(out)=0
{MODEL}
.options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27
.control
set num_threads=1
set filetype=binary
op
print v(b1) v(c1) v(x) v(b2) v(e2) @q1[ic] @q2[ic] @q1[ib] @q2[ib]
save v(src) v(rfatt) v(b1) v(c1) v(x) v(b2) v(e2) v(mod) v(b2ac) v(out) i(vsup)
tran {tmax} 200u 100u {tmax} uic
write @RAW@
quit
.endc
.end
"""


def interval_median(t, values, lo, hi):
    # Keep the central 60% of a plateau, rejecting RF/baseband transitions.
    margin = 0.2 * (hi - lo)
    mask = (t >= lo + margin) & (t <= hi - margin)
    if not np.any(mask):
        raise ValueError("Empty plateau measurement interval")
    return float(np.median(values[mask]))


def measure(raw, amp, duty):
    t = raw["time"]
    y = raw["v(out)"]
    # Complex down-conversion. A 2 MHz low-pass retains the 5 us narrow-pulse
    # plateau while rejecting the 62 MHz double-carrier component.
    mix = y * np.exp(-2j * np.pi * 31e6 * t)
    sos = butter(4, 2e6, btype="lowpass", fs=1.0 / np.median(np.diff(t)), output="sos")
    z = 2.0 * sosfiltfilt(sos, mix)
    env = np.abs(z)
    # PULSE starts high at 0 us; use the complete 100..150 us period.
    # Central plateau windows stay clear of the analysis/filter boundaries.
    p0 = 100e-6
    high = (p0, p0 + duty * 50e-6)
    low = (p0 + duty * 50e-6, p0 + 50e-6)
    ah = interval_median(t, env, *high)
    al = interval_median(t, env, *low)

    def crossing(level, expected, rising):
        window = (t[:-1] >= expected - 2e-6) & (t[:-1] <= expected + 2e-6)
        if rising:
            indices = np.where(window & (env[:-1] < level) & (env[1:] >= level))[0]
        else:
            indices = np.where(window & (env[:-1] > level) & (env[1:] <= level))[0]
        if not len(indices):
            return float("nan")
        i = indices[np.argmin(np.abs(t[indices] - expected))]
        return float(t[i] + (level - env[i]) * (t[i + 1] - t[i]) / (env[i + 1] - env[i]))

    edge_fall = p0 + duty * 50e-6
    rise50 = crossing(0.5 * (ah + al), p0, True)
    fall50 = crossing(0.5 * (ah + al), edge_fall, False)
    rise10 = crossing(al + 0.1 * (ah - al), p0, True)
    rise90 = crossing(al + 0.9 * (ah - al), p0, True)
    fall90 = crossing(al + 0.9 * (ah - al), edge_fall, False)
    fall10 = crossing(al + 0.1 * (ah - al), edge_fall, False)
    b2h = interval_median(t, raw["v(b2)"], *high)
    b2l = interval_median(t, raw["v(b2)"], *low)
    e2h = interval_median(t, raw["v(e2)"], *high)
    e2l = interval_median(t, raw["v(e2)"], *low)
    c1h = interval_median(t, raw["v(c1)"], *high)
    c1l = interval_median(t, raw["v(c1)"], *low)
    xh = interval_median(t, raw["v(x)"], *high)
    xl = interval_median(t, raw["v(x)"], *low)
    active = (t >= 110e-6) & (t <= 190e-6)
    power = float(np.mean(-5.0 * raw["i(vsup)"][active]))
    period_mask = (t >= p0) & (t <= p0 + 50e-6)
    coupling_mean_error = float(np.mean(raw["v(b2ac)"][period_mask] - raw["v(b2)"][period_mask]))
    return {
        "coupling_period_mean_error_v": coupling_mean_error,
        "amp_vpp": amp,
        "duty": duty,
        "carrier_vpp_high": 2.0 * ah,
        "carrier_vpp_low": 2.0 * al,
        "envelope_step_vpp": 2.0 * (ah - al),
        "modulation_index": (ah - al) / (ah + al),
        "envelope_duty_pct": 100.0 * (fall50 - rise50) / 50e-6,
        "envelope_rise_10_90_us": 1e6 * (rise90 - rise10),
        "envelope_fall_90_10_us": 1e6 * (fall10 - fall90),
        "mean_carrier_vpp": 2.0 * float(np.mean(env[(t >= p0) & (t <= p0 + 50e-6)])),
        "b2_plateau_v": [b2l, b2h],
        "e2_plateau_v": [e2l, e2h],
        "q2_ie_plateau_ma": [1000.0 * e2l / 470.0, 1000.0 * e2h / 470.0],
        "q1_vce_plateau_v": [c1l - xl, c1h - xh],
        "q2_vce_plateau_v": [xl - e2l, xh - e2h],
        "supply_power_mw": 1000.0 * power,
        "out_raw_min_v": float(np.min(y[active])),
        "out_raw_max_v": float(np.max(y[active])),
    }


def main():
    results = []
    for amp in (1.0, 2.0, 3.0, 4.0):
        for duty in (0.1, 0.3, 0.5):
            name = f"a{amp:g}_d{round(duty * 100):02d}"
            cir = HERE / (name + ".cir")
            raw = HERE / (name + ".raw")
            log = HERE / (name + ".log")
            text = netlist(amp, duty).replace("@RAW@", raw.as_posix())
            cir.write_text(text, encoding="utf-8", newline="\n")
            tic = time.monotonic()
            with log.open("w", encoding="utf-8", errors="replace") as stream:
                proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=HERE,
                                      stdout=stream, stderr=subprocess.STDOUT, timeout=120)
            if proc.returncode != 0 or not raw.exists():
                raise RuntimeError(f"Simulation failed: {name}; see {log}")
            item = measure(read_raw(raw), amp, duty)
            item.update(name=name, seconds=time.monotonic() - tic,
                        netlist_sha256=hashlib.sha256(cir.read_bytes()).hexdigest(),
                        raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
            results.append(item)
            print(name, f"high={item['carrier_vpp_high']:.4f} Vpp",
                  f"low={item['carrier_vpp_low']:.4f} Vpp",
                  f"step={item['envelope_step_vpp']:.4f} Vpp",
                  f"m={item['modulation_index']:.4f}")
    name = "a4_d50_r50"
    cir = HERE / (name + ".cir")
    raw = HERE / (name + ".raw")
    log = HERE / (name + ".log")
    cir.write_text(netlist(4.0, 0.5, rload="50").replace("@RAW@", raw.as_posix()),
                   encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=HERE,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    if proc.returncode != 0 or not raw.exists():
        raise RuntimeError("50 ohm load simulation failed")
    item = measure(read_raw(raw), 4.0, 0.5)
    item.update(name=name, load_ohm=50,
                netlist_sha256=hashlib.sha256(cir.read_bytes()).hexdigest(),
                raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    results.append(item)
    d50 = {r["amp_vpp"]: r for r in results if r["duty"] == 0.5 and r["amp_vpp"] in (2.0, 4.0) and "load_ohm" not in r}
    linearity = d50[2.0]["envelope_step_vpp"] / (0.5 * d50[4.0]["envelope_step_vpp"]) - 1.0
    output = {
        "scope": "Independent candidate review only; educational 2N3904 model, not the physical transistor lot",
        "source_note": "Zero-mean steady-state equivalents of AC-coupled unipolar square waves; not startup waveforms",
        "ideal_poly_reference": {
            "formula": "VAM=Vc*(0.6+0.1*V1), Vc=2 Vpp, V1=0..A",
            "a4": {"carrier_vpp_low": 1.2, "carrier_vpp_high": 2.0, "envelope_step_vpp": 0.8, "modulation_index": 0.25},
            "a2": {"carrier_vpp_low": 1.2, "carrier_vpp_high": 1.6, "envelope_step_vpp": 0.4, "modulation_index": 1.0 / 7.0},
        },
        "d50_envelope_step_linearity_error_at_2v": linearity,
        "results": results,
    }
    (HERE / "review_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("D50 envelope-step linearity error at 2 V:", f"{linearity * 100:.3f}%")


if __name__ == "__main__":
    main()
