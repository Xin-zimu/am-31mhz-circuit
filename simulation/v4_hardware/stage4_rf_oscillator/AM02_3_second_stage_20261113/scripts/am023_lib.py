# -*- coding: utf-8 -*-
"""AM-02.3 library: frozen AM-01 front end + candidate 31 MHz second stage.

The AM-01 front end is extracted verbatim from the frozen delivered netlist, so
a second-stage experiment cannot drift away from the frozen modulator. Only two
changes are made: the front-end load resistor RL is dropped (the second stage is
the load), and VMOD is re-emitted with the swept amplitude / duty.

Two-pass start-up
  pass 1  .op  -> every node voltage of the cascade; the second stage is a DC
                  network, so its OP is the correct steady state;
  pass 2  .ic from those values, v(b2ac) overridden by the modulation-coupling
                  capacitor solution, then a uic transient.
The 100 nF coupling capacitor keeps the AM-01 periodic condition:
time average of v(b2ac)-v(b2) over one 20 kHz period = 0.

Second-stage candidates
  S1  emitter-follower input buffer + CE + shunt-fed tank, capacitive tap
  S2  CE + shunt-fed tank, capacitive tap (no buffer: quantifies the loading)
  S3  CE + RFC collector load + emitter-follower output (untuned reference)
The unbypassed emitter resistor of the CE is split in two parts so that DC bias
stability and AC degeneration can be set independently:
      ea --RAX(unbypassed)--> ex --REA-- 0 ,  CEA across REA
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AM01_DIR = ROOT.parent / "AM01_2N3904_20261113"
FROZEN_CIR = AM01_DIR / "AM01_optimized_verified_4v50.cir"

RESULTS = ROOT / "results"
NETLISTS = ROOT / "netlists"
RAWS = RESULTS / "raw"
LOGS = RESULTS / "logs"
for _d in (RESULTS, NETLISTS, RAWS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AM01_DIR / "scripts"))
import am01_lib as L  # noqa: E402

L.RESULTS, L.NETLISTS, L.RAWS, L.LOGS = RESULTS, NETLISTS, RAWS, LOGS

EXE, FC, FM, PERIOD, MODEL = L.EXE, L.FC, L.FM, L.PERIOD, L.MODEL
read_raw, demodulate, time_mean, sha256 = L.read_raw, L.demodulate, L.time_mean, L.sha256
_median_plateau, _harmonic_fit = L._median_plateau, L._harmonic_fit

AM01_P = {
    "rbb": 62e3, "re": 1200.0, "rb2t": 22e3, "rb2b": 6.8e3, "rc": 1e3,
    "rb1t": 10e3, "rb1b": 10e3, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9,
    "cbb": 100e-9, "ce1": 1e-9, "cb2": 47e-12, "cout": 100e-12, "cload": 10e-12,
}
# AM-01 frozen .ic places v(b2ac) = -0.840936627907 with v(mod) = -2, so the
# steady-state voltage ACROSS CBB (v(mod)-v(b2ac)) is +1.15906 V. The solve
# parameter must therefore be the capacitor voltage, never v(b2ac)-v(b2).
VCAP_REF = 1.159063372093


def frozen_frontend():
    text = FROZEN_CIR.read_text(encoding="utf-8")
    lines, started = [], False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("VSUP "):
            started = True
        if not started or not s or s.startswith("*") or s.startswith("VMOD "):
            continue
        lines.append(s)
        if s.startswith("COUT "):
            break
    if not lines or not lines[-1].startswith("COUT "):
        raise RuntimeError("frozen front end not extracted")
    return "\n".join(lines)


FRONTEND = frozen_frontend()


def _ce(p):
    return f"""RBAT vcc ba {p['rbat']:.6g}
RBAB ba 0 {p['rbab']:.6g}
QA ca ba ea 2N3904
RAX ea ex {p['rax']:.6g}
REA ex 0 {p['rea']:.6g}
CEA ex 0 {p['cea']:.6g}"""


def _tank(p):
    return f"""LTANK vcc ca {p['ltank']:.6g}
CT1 ca rl {p['ct1']:.6g}
CT2 rl 0 {p['ct2']:.6g}
RLD rl 0 {p['rload']:.6g}
CLD rl 0 {p['cload']:.6g}"""


def stage_s1(p):
    return f"""* --- S1: EF input buffer + CE + shunt-fed tank + capacitive tap
CIN2 {p['in_node']} ba_s {p['cin2']:.6g}
RB1 vcc ba_s {p['rb1']:.6g}
RB2 ba_s 0 {p['rb2']:.6g}
QF vcc ba_s ef 2N3904
REF ef 0 {p['ref']:.6g}
CC1 ef bi {p['cc1']:.6g}
RBT vcc bi {p['rbat']:.6g}
RBB2 bi 0 {p['rbab']:.6g}
QA ca bi ea 2N3904
RAX ea ex {p['rax']:.6g}
REA ex 0 {p['rea']:.6g}
CEA ex 0 {p['cea']:.6g}
{_tank(p)}"""


def stage_s2(p):
    return f"""* --- S2: CE + shunt-fed tank + capacitive tap (no input buffer)
CIN2 {p['in_node']} ba {p['cin2']:.6g}
{_ce(p)}
{_tank(p)}"""


def stage_s3(p):
    return f"""* --- S3: CE + RFC collector load + emitter-follower output (untuned)
CIN2 {p['in_node']} ba {p['cin2']:.6g}
{_ce(p)}
LRFC vcc ca {p['lrfc']:.6g}
QB vcc ca eb 2N3904
REB eb 0 {p['reb']:.6g}
COUT2 eb rl {p['cout2']:.6g}
RLD rl 0 {p['rload']:.6g}
CLD rl 0 {p['cload']:.6g}"""


def stage_s4(p):
    return f"""* --- S4: cascode (CE + grounded-base) + shunt-fed tank + capacitive tap
CIN2 {p['in_node']} ba {p['cin2']:.6g}
RBAT vcc ba {p['rbat']:.6g}
RBAB ba 0 {p['rbab']:.6g}
QA ca1 ba ea 2N3904
RAX ea ex {p['rax']:.6g}
REA ex 0 {p['rea']:.6g}
CEA ex 0 {p['cea']:.6g}
QC ca xb ca1 2N3904
RBX1 vcc xb {p['rbx1']:.6g}
RBX2 xb 0 {p['rbx2']:.6g}
CBX xb 0 {p['cbx']:.6g}
{_tank(p)}"""

def stage_sa(p):
    """Frozen AM-02.2 scheme A, reproduced element for element."""
    return f"""* --- AM-02.2 scheme A (frozen) + measurement load
VJ {p['in_node']} ba_a DC 0   $ DC-coupled junction, as AM-02.2 froze it
R1 vcc ba_a 33k
R2 ba_a 0 6.8k
QAA ca_a ba_a ea_a 2N3904
RE1 ea_a 0 100
RC1 vcc ca_a 1k
COUTA ca_a rl {p['couta']:.6g}
RLD rl 0 {p['rload']:.6g}
CLD rl 0 {p['cload']:.6g}"""

def stage_s6(p):
    """S6: CE + tank/tap with an L-match at the input (150 ohm -> ~27 ohm)."""
    return f"""* --- S6: CE + shunt-fed tank + capacitive tap + input L-match
CIN6 {p['in_node']} n6 {p['cin6']:.6g}
CM n6 0 {p['cm']:.6g}
LM n6 nb {p['lm']:.6g}
RSER nb bi {p['rser']:.6g}
RBT vcc bi {p['rbat']:.6g}
RBB2 bi 0 {p['rbab']:.6g}
QA ca bi ea 2N3904
RAX ea ex {p['rax']:.6g}
REA ex 0 {p['rea']:.6g}
CEA ex 0 {p['cea']:.6g}
LTANK vcc ca {p['ltank']:.6g}
CT1 ca rl {p['ct1']:.6g}
CT2 rl 0 {p['ct2']:.6g}
RLD rl 0 {p['rload']:.6g}
CLD rl 0 {p['cload']:.6g}"""

STAGES = {"S1": stage_s1, "S2": stage_s2, "S3": stage_s3, "S4": stage_s4, "SA": stage_sa, "S6": stage_s6}
STAGE_NODES = {
    "S1": ["ba_s", "ef", "bi", "ea", "ex", "ca", "rl"],
    "S2": ["ba", "ea", "ex", "ca", "rl"],
    "S3": ["ba", "ea", "ex", "ca", "eb", "rl"],
    "S4": ["ba", "ea", "ex", "ca1", "xb", "ca", "rl"],
    "SA": ["ba_a", "ea_a", "ca_a", "in6", "n6", "nb", "bi", "rl"],
    "S6": ["bi", "ea", "ex", "ca", "rl"],
}
DRIVE = {"S1": "ba_s", "S2": "ba", "S3": "ba", "S4": "ba", "SA": "ba_a",
         "S6": "in6"}


def default_stage(topology):
    base = {"in_node": "out", "cin2": 100e-9, "rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
            "rea": 100.0, "cea": 1e-9, "ltank": 1.0e-6, "ct1": 36e-12,
            "ct2": 66e-12, "rload": 50.0, "cload": 10e-12}
    if topology == "S1":
        base.update({"rb1": 100e3, "rb2": 100e3, "ref": 900.0, "cc1": 1e-9})
    if topology == "S3":
        base.update({"lrfc": 2.2e-6, "reb": 180.0, "cout2": 100e-9})
    if topology == "S4":
        base.update({"rbx1": 10e3, "rbx2": 10e3, "cbx": 100e-9})
    if topology == "SA":
        base.update({"cina": 100e-9, "couta": 100e-12})
    if topology == "S6":
        base.update({"cin6": 10e-9, "cm": 100e-12, "lm": 0.22e-6, "rser": 0.0, "rbat": 2.2e3, "rbab": 1.1e3,
                     "rax": 5.0, "rea": 39.0, "ltank": 0.47e-6,
                     "ct1": 100e-12, "ct2": 56e-12})
    return base


# ------------------------------------------------------------------ netlists
def _ic_all(state):
    order = ["vcc", "src", "rfatt", "b1", "c1", "x", "b2", "e2", "mod", "b2ac",
             "out", "ba_s", "ef", "bi", "ba", "ea", "ex", "ca1", "xb", "ca", "eb",
             "ba_a", "ea_a", "ca_a", "in6", "n6", "nb", "bi", "rl"]
    parts = [f"v({n})={state[n]:.10g}" for n in order if n in state]
    for n in sorted(state):
        if n not in order:
            parts.append(f"v({n})={state[n]:.10g}")
    rows = [parts[i:i + 5] for i in range(0, len(parts), 5)]
    return ".ic " + "\n+ ".join(" ".join(r) for r in rows)


def build(topology, stage=None, amp=4.0, duty=0.5, state=None, stop_us=130.0,
          tmax_ns=0.5, mode="tran", raw_name="run.raw"):
    p = dict(default_stage(topology), **(stage or {}))
    low, high, delay = -amp * duty, amp * (1.0 - duty), 25e-6
    width = duty * PERIOD - 40e-9
    if width <= 0:
        raise ValueError("duty too small")
    ic = _ic_all(state) if state else ""
    uic = " uic" if ic else ""
    dcpath = "" if topology == "SA" else "RLK out 0 10k   $ interface DC return"
    body = f"""* AM-01 (frozen) + AM-02.3 stage {topology}, {amp:g} Vpp, duty {duty:.2f}
{FRONTEND}
* AM-01 "out" carries no DC path of its own (COUT blocks it). A capacitively
* coupled second stage must therefore supply one, otherwise the operating
* point of that node is undefined and ngspice reports a singular matrix.
{dcpath}
{STAGES[topology](p)}
VMOD mod 0 PULSE({low:.12g} {high:.12g} {delay:.12g} 20n 20n {width:.12g} 50u)"""
    if mode == "op":
        control = f"""set num_threads=1
set filetype=binary
op
write {raw_name}
quit"""
    else:
        save = "save v(out) v(rl) v(b2) v(b2ac) v(c1) v(x) v(e2) v(mod) i(vsup)"
        for node in STAGE_NODES[topology]:
            save += f" v({node})"
        control = f"""set num_threads=1
set filetype=binary
op
{save}
tran {tmax_ns}n {stop_us}u 0 {tmax_ns}n{uic}
write {raw_name}
quit"""
    return f"""{body}
{ic}
{MODEL}
.options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27
.control
{control}
.endc
.end
"""


def standalone(topology, stage=None, vcc=5.0, stop_us=50.0, mode="ac",
              raw_name="st.raw", amp_v=0.05, freq=31e6):
    """Stage alone, driven by an ideal source through a 100 nF coupling cap."""
    p = {**default_stage(topology), **(stage or {}), "in_node": "in0"}
    body = f"""* AM-02.3 stage {topology} standalone
VCCX vcc 0 DC {vcc:.6g}
VS in0 0 DC 0 AC 1
{STAGES[topology](p)}
{MODEL}
.options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27
.control
set num_threads=1
set filetype=binary
op
"""
    if mode == "ac":
        body += f"""ac dec 80 5meg 120meg
write {raw_name}
quit
.endc
.end
"""
    else:
        body = body.replace('VS in0 0 DC 0 AC 1',
                            f'VSINX in0 0 DC 0 SIN(0 {amp_v:g} {freq:g})')
        body += f"""save v(in0) v(rl) v(ca) v(ea) i(vccx) i(vsinx)
tran 0.5n {stop_us}u 0 0.5n
write {raw_name}
quit
.endc
.end
"""
    return body


def run(name, text, timeout=900):
    cir = NETLISTS / (name + ".cir")
    cir.write_text(text, encoding="utf-8", newline="\n")
    log = LOGS / (name + ".log")
    tic = time.monotonic()
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=str(RESULTS),
                              stdout=stream, stderr=subprocess.STDOUT,
                              timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed for {name}; see {log}")
    return {"cir": cir, "log": log, "seconds": time.monotonic() - tic}


# --------------------------------------------------------------- raw readers
def read_raw_ac(path):
    """Binary raw reader that is complex-aware (AC plots)."""
    blob = Path(path).read_bytes()
    marker = b"Binary:\n"
    end = blob.find(marker)
    if end < 0:
        raise ValueError("binary raw expected")
    head = blob[:end].decode("latin-1").replace("\r", "")
    nvar = int(re.search(r"No\. Variables:\s+(\d+)", head).group(1))
    npt = int(re.search(r"No\. Points:\s+(\d+)", head).group(1))
    names = re.findall(r"(?m)^\s*\d+\s+(\S+)\s+(?:voltage|current|time|frequency)\b", head)
    if len(names) != nvar:
        raise ValueError(f"raw variable count mismatch {len(names)} vs {nvar}")
    width = 2 if "complex" in head else 1
    start = end + len(marker)
    arr = np.frombuffer(blob[start:start + npt * nvar * width * 8],
                        dtype=np.float64).reshape(npt, nvar, width)
    arr = arr[:, :, 0] + 1j * arr[:, :, 1] if width == 2 else arr[:, :, 0]
    return {name: arr[:, i] for i, name in enumerate(names)}


def ac_metrics(raw_path, f0=FC):
    d = read_raw_ac(raw_path)
    f = np.real(d["frequency"])
    gain = np.abs(d["v(rl)"] / d["v(in0)"])
    zc = -d["v(in0)"] / d["i(vs)"]
    i0 = int(np.argmin(np.abs(f - f0)))
    return (
        {
            "gain_db": float(20 * np.log10(gain[i0])),
            "gain_lin": float(gain[i0]),
            "zin_real": float(np.real(zc[i0])),
            "zin_imag": float(np.imag(zc[i0])),
            "zin_mag": float(abs(zc[i0])),
            "zin_equiv_pf": float(1e12 / (2 * np.pi * f0 * abs(np.imag(zc[i0]))))
            if np.imag(zc[i0]) < 0 else None,
            "f_peak_mhz": float(f[int(np.argmax(gain))] / 1e6),
            "gain_at_minus20k_db": float(20 * np.log10(gain[int(np.argmin(np.abs(f - (f0 - 20e3))))])),
            "gain_at_plus20k_db": float(20 * np.log10(gain[int(np.argmin(np.abs(f - (f0 + 20e3))))])),
            "raw": str(raw_path),
        },
        f,
        gain,
    )


# ---------------------------------------------------------------- transient
def op_state(topology, stage=None, tag="op"):
    raw_name = f"{tag}_{topology}.raw"
    info = run(f"{tag}_{topology}",
               build(topology, stage, mode="op", raw_name=raw_name), timeout=180)
    data = read_raw(RESULTS / raw_name)
    nodes = {k[2:-1]: float(v[0]) for k, v in data.items()
             if k.startswith("v(") and k.endswith(")")}
    return {"nodes": nodes, "log": str(info["log"])}


def solve_cap(topology, stage=None, amp=4.0, duty=0.5, stop_us=50.0,
              v0=None, tol=2e-4, max_iter=5, tag=None):
    op = op_state(topology, stage, tag=f"op_{tag or topology}")
    v = VCAP_REF if v0 is None else v0
    history, v_prev, g_prev = [], None, None
    tag = tag or f"cap_{topology}"
    for it in range(max_iter):
        state = dict(op["nodes"])
        state["b2ac"] = -amp * duty + v
        name = f"{tag}_it{it}"
        raw_name = name + ".raw"
        run(name, build(topology, stage, amp, duty, state=state,
                        stop_us=stop_us, raw_name=raw_name), timeout=900)
        data = read_raw(RESULTS / raw_name)
        g = time_mean(data["time"], data["v(b2ac)"] - data["v(b2)"])
        history.append({"iteration": it, "vcap": v, "residual": g})
        print(f"  cap {it}: Vcap={v:.6f} V, <b2ac-b2>={g*1e3:.4f} mV")
        if abs(g) < tol:
            break
        if v_prev is None:
            v_next = v + 0.05
        else:
            den = g - g_prev
            v_next = v + 0.05 if abs(den) < 1e-15 else v - g * (v - v_prev) / den
        v_prev, g_prev = v, g
        v = v_next
    else:
        raise RuntimeError("cap solve did not converge")
    return {"vcap": v, "residual": g, "iterations": history, "op": op}


def _band(t, vec, lo, hi, margin=0.2):
    m = margin * (hi - lo)
    mask = (t >= lo + m) & (t <= hi - m)
    return float(np.median(vec[mask]))


def measure(raw_path, topology, duty, p0_us=75.0, load_r=50.0):
    data = read_raw(raw_path)
    t = data["time"]
    y = data["v(rl)"]
    env = demodulate(t, y)
    p0 = p0_us * 1e-6
    high = (p0, p0 + duty * PERIOD)
    low = (p0 + duty * PERIOD, p0 + PERIOD)
    ah = _median_plateau(t, env, *high)
    al = _median_plateau(t, env, *low)
    step = ah - al

    def extreme(lo, hi):
        m = 0.2 * (hi - lo)
        mask = (t >= lo + m) & (t <= hi - m)
        return float(np.min(env[mask])), float(np.max(env[mask]))

    hmin, hmax = extreme(*high)
    lmin, lmax = extreme(*low)
    central = (t >= p0 + 5e-6) & (t <= low[1] - 5e-6)
    win_h = (t >= high[0] + 0.2 * (high[1] - high[0])) & (t <= high[1] - 0.2 * (high[1] - high[0]))
    win_l = (t >= low[0] + 0.2 * (low[1] - low[0])) & (t <= low[1] - 0.2 * (low[1] - low[0]))
    thd_h = _harmonic_fit(t[win_h], y[win_h], FC)
    thd_l = _harmonic_fit(t[win_l], y[win_l], FC)

    if "v(ca)" in data:
        ca, ea = data["v(ca)"], data["v(ea)"]
    else:
        ca, ea = data["v(ca_a)"], data["v(ea_a)"]
    out = {
        "duty_pct": 100.0 * duty,
        "load_ohm": load_r,
        "vpp_high": 2.0 * ah,
        "vpp_low": 2.0 * al,
        "step_vpp": 2.0 * step,
        "modulation_index": step / (ah + al),
        "mean_vpp": 2.0 * float(np.mean(env[(t >= p0) & (t <= p0 + PERIOD)])),
        "plateau_flatness": max(hmax - hmin, lmax - lmin) / step if step else float("inf"),
        "overshoot": max(0.0, hmax - ah, al - lmin) / step if step else float("inf"),
        "thd_high_pct": 100.0 * thd_h["thd"],
        "thd_low_pct": 100.0 * thd_l["thd"],
        "rl_min_v": float(np.min(y[(t >= p0) & (t <= p0 + PERIOD)])),
        "rl_max_v": float(np.max(y[(t >= p0) & (t <= p0 + PERIOD)])),
        "supply_mw": 1000.0 * time_mean(t, -5.0 * data["i(vsup)"], central),
        "supply_ma": 1000.0 * time_mean(t, -data["i(vsup)"], central),
        "ca_high_v": _band(t, ca, *high),
        "ca_low_v": _band(t, ca, *low),
        "ca_min_v": float(np.min(ca[(t >= p0) & (t <= p0 + PERIOD)])),
        "ca_max_v": float(np.max(ca[(t >= p0) & (t <= p0 + PERIOD)])),
        "ea_high_v": _band(t, ea, *high),
        "qa_vce_high_v": _band(t, ca, *high) - _band(t, ea, *high),
        "qa_vce_low_v": _band(t, ca, *low) - _band(t, ea, *low),
        "envelope_high_mw": 1000.0 * (2.0 * ah) ** 2 / (8.0 * load_r),
    }
    if topology == "S1":
        out["bi_dc_v"] = _band(t, data["v(bi)"], *high)
        out["ef_dc_v"] = _band(t, data["v(ef)"], *high)
        out["ba_s_dc_v"] = _band(t, data["v(ba_s)"], *high)
    return out
