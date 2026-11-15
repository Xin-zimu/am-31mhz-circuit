# -*- coding: utf-8 -*-
"""AM-01 shared simulation and measurement library.

The 100 nF modulation-coupling capacitor is solved from its true periodic
condition: its average voltage must make the average current in RBB zero.
A short shooting/secant solve therefore replaces either an arbitrary .ic or
an impractically long transient for every matrix point. A separate cold-start
run checks that the solved state agrees with the physical RC settling.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import time

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
NETLISTS = ROOT / "netlists"
RAWS = RESULTS / "raw"
LOGS = RESULTS / "logs"
for directory in (RESULTS, NETLISTS, RAWS, LOGS):
    directory.mkdir(parents=True, exist_ok=True)

EXE = Path("D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe")
FC = 31e6
FM = 20e3
PERIOD = 50e-6
MODEL = """.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)"""

DEFAULT = {
    "rbb": 82e3,
    "re": 470.0,
    "rb2t": 22e3,
    "rb2b": 6.8e3,
    "rc": 1e3,
    "rb1t": 10e3,
    "rb1b": 10e3,
    "rin": 10e3,
    "rsh": 100.0,
    "cin": 100e-12,
    "cbb": 100e-9,
    "ce1": 1e-9,
    "cb2": 47e-12,
    "cout": 100e-12,
    "cload": 10e-12,
}

NOMINAL_DC = {
    "vcc": 5.0,
    "src": 0.0,
    "rfatt": 0.0,
    "b1": 2.463100,
    "c1": 4.002394,
    "x": 1.797899,
    "b2": 1.141575,
    "e2": 0.4758707,
    "out": 0.0,
}


def time_mean(t, y, mask=None):
    """Trapezoidal time average; ngspice timesteps are not uniformly spaced."""
    if mask is not None:
        t = t[mask]
        y = y[mask]
    if len(t) < 2:
        raise ValueError("Need at least two samples for a time average")
    return float(np.trapezoid(y, t) / (t[-1] - t[0]))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def _ic_line(state):
    if not state:
        return ""
    order = ("vcc", "src", "rfatt", "b1", "c1", "x", "b2", "e2", "mod", "b2ac", "out")
    return ".ic " + " ".join(f"v({node})={state[node]:.12g}" for node in order)


def build_netlist(p, amp, duty, load_r, state=None, carrier=True, cold=False,
                  stop_us=130.0, tmax_ns=0.5, raw_name="run.raw"):
    p = dict(DEFAULT, **(p or {}))
    if cold:
        # Real unipolar 0..A waveform, no delay and no initial-condition shortcut.
        high, low, delay = amp, 0.0, 0.0
    else:
        # Zero-mean steady equivalent of the same AC-coupled square wave.
        high, low, delay = amp * (1.0 - duty), -amp * duty, 25e-6
    width = duty * PERIOD - 40e-9
    if width <= 0:
        raise ValueError("Pulse width must exceed 40 ns total edges")
    vr = "SIN(0 1 31meg)" if carrier else "0"
    ic = "" if cold else _ic_line(state)
    uic = " uic" if ic else ""
    return f"""* AM-01 two-2N3904 modulator, RBB={p['rbb']:.0f}, RE={p['re']:.0f}, RL={load_r:.0f}
VSUP vcc 0 DC 5
CDEC1 vcc 0 100n
CDEC2 vcc 0 10u
VRF src 0 {vr}
RIN src rfatt {p['rin']:.12g}
RSH rfatt 0 {p['rsh']:.12g}
CIN rfatt b1 {p['cin']:.12g}
RB1T vcc b1 {p['rb1t']:.12g}
RB1B b1 0 {p['rb1b']:.12g}
Q1 c1 b1 x 2N3904
RC vcc c1 {p['rc']:.12g}
CE1 x 0 {p['ce1']:.12g}
Q2 x b2 e2 2N3904
RB2T vcc b2 {p['rb2t']:.12g}
RB2B b2 0 {p['rb2b']:.12g}
RE e2 0 {p['re']:.12g}
CB2 b2 0 {p['cb2']:.12g}
VMOD mod 0 PULSE({low:.12g} {high:.12g} {delay:.12g} 20n 20n {width:.12g} 50u)
CBB mod b2ac {p['cbb']:.12g}
RBB b2ac b2 {p['rbb']:.12g}
COUT c1 out {p['cout']:.12g}
RL out 0 {load_r:.12g}
CL out 0 {p['cload']:.12g}
{ic}
{MODEL}
.options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27
.control
set num_threads=1
set filetype=binary
op
print v(b1) v(c1) v(x) v(b2) v(e2) @q1[ic] @q2[ic] @q1[ib] @q2[ib]
save v(src) v(rfatt) v(b1) v(c1) v(x) v(b2) v(e2) v(mod) v(b2ac) v(out) i(vsup)
tran {tmax_ns}n {stop_us}u 0 {tmax_ns}n{uic}
write {raw_name}
quit
.endc
.end
"""


def run(p, amp, duty, load_r, state=None, carrier=True, cold=False,
        stop_us=130.0, tmax_ns=0.5, tag="run"):
    p = dict(DEFAULT, **(p or {}))
    name = f"{tag}_rbb{p['rbb']/1e3:g}k_re{p['re']:g}_a{amp:g}_d{round(duty*100):02d}_rl{load_r:g}"
    cir = NETLISTS / (name + ".cir")
    raw = RAWS / (name + ".raw")
    log = LOGS / (name + ".log")
    cir.write_text(build_netlist(p, amp, duty, load_r, state, carrier, cold,
                                 stop_us, tmax_ns, raw.as_posix()),
                   encoding="utf-8", newline="\n")
    tic = time.monotonic()
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    if proc.returncode != 0 or not raw.exists():
        raise RuntimeError(f"ngspice failed for {name}; see {log}")
    return {
        "name": name,
        "params": p,
        "amp": amp,
        "duty": duty,
        "load_r": load_r,
        "cir": str(cir),
        "raw": str(raw),
        "log": str(log),
        "seconds": time.monotonic() - tic,
        "cir_sha256": sha256(cir),
        "raw_sha256": sha256(raw),
        "log_sha256": sha256(log),
    }


def base_state(cap_voltage, low):
    state = dict(NOMINAL_DC)
    state["mod"] = low
    state["b2ac"] = low + cap_voltage
    return state


def periodic_cap_solve(p, amp, duty, load_r, tag, verbose=True, max_iter=6):
    """Solve average(v(b2ac)-v(b2))=0 by secant iterations on Vcap."""
    low = -amp * duty
    v0 = NOMINAL_DC["b2"]
    history = []
    v_prev = None
    g_prev = None
    v = v0
    for iteration in range(max_iter):
        state = base_state(v, low)
        info = run(p, amp, duty, load_r, state=state, stop_us=50.0,
                   tag=f"{tag}_shoot{iteration}")
        data = read_raw(info["raw"])
        g = time_mean(data["time"], data["v(b2ac)"] - data["v(b2)"])
        history.append({"iteration": iteration, "vcap": v, "g": g,
                        "netlist": info["cir"], "raw_sha256": info["raw_sha256"]})
        if verbose:
            print(f"  cap {iteration}: V={v:.6f} V, <b2ac-b2>={g*1e3:.4f} mV")
        if abs(g) < 2e-4:
            break
        if v_prev is None:
            v_next = v + 0.05
        else:
            denominator = g - g_prev
            if abs(denominator) < 1e-12:
                v_next = v + 0.05
            else:
                v_next = v - g * (v - v_prev) / denominator
        v_prev, g_prev = v, g
        v = v_next
    else:
        raise RuntimeError("Coupling-capacitor periodic solve did not converge")
    return {"vcap": v, "residual_v": g, "iterations": history}


def demodulate(t, y):
    dt = float(np.median(np.diff(t)))
    mix = y * np.exp(-2j * np.pi * FC * t)
    sos = butter(4, 2e6, btype="lowpass", fs=1.0 / dt, output="sos")
    return np.abs(2.0 * sosfiltfilt(sos, mix))


def _median_plateau(t, values, lo, hi):
    margin = 0.2 * (hi - lo)
    mask = (t >= lo + margin) & (t <= hi - margin)
    if np.count_nonzero(mask) < 10:
        raise ValueError("Plateau window has too few samples")
    return float(np.median(values[mask]))


def _crossing(t, y, level, expected, rising):
    window = (t[:-1] >= expected - 2e-6) & (t[:-1] <= expected + 2e-6)
    if rising:
        indices = np.where(window & (y[:-1] < level) & (y[1:] >= level))[0]
    else:
        indices = np.where(window & (y[:-1] > level) & (y[1:] <= level))[0]
    if not len(indices):
        return float("nan")
    index = indices[np.argmin(np.abs(t[indices] - expected))]
    return float(t[index] + (level - y[index]) * (t[index + 1] - t[index])
                 / (y[index + 1] - y[index]))


def _harmonic_fit(t, y, frequency, count=5):
    dt = float(np.median(np.diff(t)))
    # Use an integer number of carrier cycles near the centre of the window.
    cycles = max(3, int((t[-1] - t[0]) * frequency))
    duration = cycles / frequency
    centre = 0.5 * (t[0] + t[-1])
    mask = (t >= centre - duration / 2) & (t <= centre + duration / 2)
    ts = t[mask]
    ys = y[mask] - np.mean(y[mask])
    columns = [np.ones_like(ts)]
    for k in range(1, count + 1):
        columns.extend([np.sin(2 * np.pi * k * frequency * ts),
                        np.cos(2 * np.pi * k * frequency * ts)])
    matrix = np.vstack(columns).T
    coefficients, *_ = np.linalg.lstsq(matrix, ys, rcond=None)
    amplitudes = np.hypot(coefficients[1::2], coefficients[2::2])
    residual = ys - matrix @ coefficients
    thd = float(np.linalg.norm(amplitudes[1:]) / amplitudes[0]) if amplitudes[0] else float("inf")
    return {
        "fundamental_vpp": 2.0 * float(amplitudes[0]),
        "thd": thd,
        "residual_rms_v": float(np.sqrt(np.mean(residual ** 2))),
        "cycles": cycles,
    }


def measure(info, p0_us=75.0, compare_period=True):
    data = read_raw(info["raw"])
    t = data["time"]
    y = data["v(out)"]
    env = demodulate(t, y)
    p0 = p0_us * 1e-6
    duty = info["duty"]
    high = (p0, p0 + duty * PERIOD)
    low = (p0 + duty * PERIOD, p0 + PERIOD)
    ah = _median_plateau(t, env, *high)
    al = _median_plateau(t, env, *low)
    step = ah - al
    mid = 0.5 * (ah + al)
    rise50 = _crossing(t, env, mid, high[0], True)
    fall50 = _crossing(t, env, mid, high[1], False)
    rise10 = _crossing(t, env, al + 0.1 * step, high[0], True)
    rise90 = _crossing(t, env, al + 0.9 * step, high[0], True)
    fall90 = _crossing(t, env, al + 0.9 * step, high[1], False)
    fall10 = _crossing(t, env, al + 0.1 * step, high[1], False)

    def plateau_extreme(lo, hi):
        margin = 0.2 * (hi - lo)
        mask = (t >= lo + margin) & (t <= hi - margin)
        return float(np.min(env[mask])), float(np.max(env[mask]))

    hmin, hmax = plateau_extreme(*high)
    lmin, lmax = plateau_extreme(*low)
    flatness = max(hmax - hmin, lmax - lmin) / step if step else float("inf")
    overshoot = max(0.0, hmax - ah, al - lmin) / step if step else float("inf")

    central = (t >= p0 + 5e-6) & (t <= low[1] - 5e-6)
    i_rf = data["i(vsup)"][central]
    c1 = data["v(c1)"]
    x = data["v(x)"]
    e2 = data["v(e2)"]
    b2 = data["v(b2)"]

    thd_high = _harmonic_fit(t[(t >= high[0] + 0.2 * (high[1] - high[0]))
                               & (t <= high[1] - 0.2 * (high[1] - high[0]))],
                             y[(t >= high[0] + 0.2 * (high[1] - high[0]))
                               & (t <= high[1] - 0.2 * (high[1] - high[0]))], FC)
    thd_low = _harmonic_fit(t[(t >= low[0] + 0.2 * (low[1] - low[0]))
                              & (t <= low[1] - 0.2 * (low[1] - low[0]))],
                            y[(t >= low[0] + 0.2 * (low[1] - low[0]))
                              & (t <= low[1] - 0.2 * (low[1] - low[0]))], FC)

    result = {
        "name": info["name"],
        "rbb_ohm": info["params"]["rbb"],
        "re_ohm": info["params"]["re"],
        "amp_vpp": info["amp"],
        "duty_pct": 100.0 * duty,
        "load_ohm": info["load_r"],
        "carrier_vpp_high": 2.0 * ah,
        "carrier_vpp_low": 2.0 * al,
        "envelope_step_vpp": 2.0 * step,
        "modulation_index": step / (ah + al),
        "mean_carrier_vpp": 2.0 * float(np.mean(env[(t >= p0) & (t <= p0 + PERIOD)])),
        "envelope_duty_pct": 100.0 * (fall50 - rise50) / PERIOD,
        "rise_10_90_us": 1e6 * (rise90 - rise10),
        "fall_90_10_us": 1e6 * (fall10 - fall90),
        "plateau_flatness": float(flatness),
        "envelope_overshoot": float(overshoot),
        "carrier_thd_high": thd_high["thd"],
        "carrier_thd_low": thd_low["thd"],
        "rf_out_min_v": float(np.min(y[(t >= p0) & (t <= p0 + PERIOD)])),
        "rf_out_max_v": float(np.max(y[(t >= p0) & (t <= p0 + PERIOD)])),
        "supply_power_mw": 1000.0 * time_mean(t, -5.0 * data["i(vsup)"], central),
        "dc_c1_mean_v": float(np.mean(c1[central])),
        "q1_ic_high_ma": 1000.0 * (5.0 - _median_plateau(t, c1, *high)) / info["params"]["rc"],
        "q1_ic_low_ma": 1000.0 * (5.0 - _median_plateau(t, c1, *low)) / info["params"]["rc"],
        "q2_ie_high_ma": 1000.0 * _median_plateau(t, e2, *high) / info["params"]["re"],
        "q2_ie_low_ma": 1000.0 * _median_plateau(t, e2, *low) / info["params"]["re"],
        "q1_vce_high_v": _median_plateau(t, c1, *high) - _median_plateau(t, x, *high),
        "q1_vce_low_v": _median_plateau(t, c1, *low) - _median_plateau(t, x, *low),
        "q2_vce_high_v": _median_plateau(t, x, *high) - _median_plateau(t, e2, *high),
        "q2_vce_low_v": _median_plateau(t, x, *low) - _median_plateau(t, e2, *low),
        "b2_high_v": _median_plateau(t, b2, *high),
        "b2_low_v": _median_plateau(t, b2, *low),
        "cir": info["cir"],
        "raw": info["raw"],
        "cir_sha256": info["cir_sha256"],
        "raw_sha256": info["raw_sha256"],
    }
    mask = (t >= p0) & (t <= p0 + PERIOD)
    result["coupling_residual_v"] = time_mean(
        t, data["v(b2ac)"] - data["v(b2)"], mask)
    if compare_period and p0_us >= 50:
        q0 = p0 - PERIOD
        high0 = (q0, q0 + duty * PERIOD)
        low0 = (q0 + duty * PERIOD, q0 + PERIOD)
        a_h0 = _median_plateau(t, env, *high0)
        a_l0 = _median_plateau(t, env, *low0)
        result["period_to_period_high_pct"] = 100.0 * (a_h0 / ah - 1.0)
        result["period_to_period_low_pct"] = 100.0 * (a_l0 / al - 1.0)
    return result


def evaluate_case(p, amp, duty, load_r, tag, keep_raw=False, verbose=True):
    solve = periodic_cap_solve(p, amp, duty, load_r, tag, verbose=verbose)
    low = -amp * duty
    state = base_state(solve["vcap"], low)
    info = run(p, amp, duty, load_r, state=state, stop_us=130.0,
               tag=f"{tag}_final")
    metrics = measure(info)
    metrics.update({
        "cap_solution": solve,
        "periodic_residual_mv": 1000.0 * solve["residual_v"],
        "final_coupling_residual_mv": 1000.0 * metrics["coupling_residual_v"],
        "simulation_seconds": info["seconds"],
    })
    if not keep_raw:
        Path(info["raw"]).unlink(missing_ok=True)
        metrics["raw"] = None
        metrics["raw_note"] = "Deleted after measurement; netlist, log and SHA-256 retained"
    return metrics
