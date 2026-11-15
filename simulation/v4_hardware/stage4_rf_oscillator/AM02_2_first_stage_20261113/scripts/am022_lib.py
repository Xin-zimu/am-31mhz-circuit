# -*- coding: utf-8 -*-
"""AM-02.2 candidate first-stage comparison library.

Candidates:
A: 2N3904 common emitter with unbypassed 100 ohm emitter degeneration
B: 2N3904 common base
C: A followed by an emitter follower (CE -> EF)
D: 2N3904 cascode (CE -> CB), extra candidate because Miller capacitance is
   the dominant input-loading mechanism of A/C
E: EF input buffer followed by CE (the reverse order of C)
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
NETLISTS = ROOT / "netlists"
RAWS = RESULTS / "raw"
LOGS = RESULTS / "logs"
for d in (RESULTS, NETLISTS, RAWS, LOGS):
    d.mkdir(parents=True, exist_ok=True)

EXE = Path("D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe")
MODEL = """.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)"""


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_raw(path):
    blob = Path(path).read_bytes()
    marker = b"Binary:\n"
    end = blob.find(marker)
    if end < 0:
        raise ValueError("binary raw required")
    head = blob[:end].decode("latin-1").replace("\r", "")
    nvar = int(re.search(r"No\. Variables:\s+(\d+)", head).group(1))
    npt = int(re.search(r"No\. Points:\s+(\d+)", head).group(1))
    names = re.findall(r"(?m)^\s*\d+\s+(\S+)\s+(?:voltage|current|time)\s*$", head)
    if len(names) != nvar:
        raise ValueError("variable count mismatch")
    start = end + len(marker)
    arr = np.frombuffer(blob[start:start + npt * nvar * 8], dtype=np.float64).reshape(npt, nvar)
    return {name: np.ascontiguousarray(arr[:, i]) for i, name in enumerate(names)}


def circuit(candidate, load=10000.0):
    """Return the circuit body; input node is b, except B uses e."""
    head = "VCC vcc 0 DC 5\n"
    tail = f"""COUT {candidate_out(candidate)} out 100p
RL out 0 {load:.12g}
CL out 0 10p
"""
    if candidate == "A":
        body = """R1 vcc b 33k
R2 b 0 6.8k
Q1 c b e 2N3904
RE1 e 0 100
RC1 vcc c 1k
"""
    elif candidate == "B":
        body = """R1 vcc b 10k
R2 b 0 10k
CB b 0 100n
Q1 c b e 2N3904
RE1 e 0 1k
RC1 vcc c 1k
"""
    elif candidate == "C":
        body = """R1 vcc b 33k
R2 b 0 6.8k
Q1 c b e 2N3904
RE1 e 0 100
RC1 vcc c 1k
Q2 vcc c e2 2N3904
RE2 e2 0 2.2k
"""
    elif candidate == "D":
        body = """R1 vcc b 33k
R2 b 0 10k
Q1 x b e 2N3904
RE1 e 0 470
CE1 e 0 1n
R3 vcc b2 10k
R4 b2 0 10k
CB2 b2 0 100n
Q2 c2 b2 x 2N3904
RC1 vcc c2 1k
"""
    elif candidate == "E":
        body = """R1 vcc b1 100k
R2 b1 0 100k
Q1 vcc b1 e1 2N3904
RE1 e1 0 2.2k
C1 e1 b2 1n
R3 vcc b2 33k
R4 b2 0 6.8k
Q2 c2 b2 e2 2N3904
RE2 e2 0 100
RC1 vcc c2 1k
"""
    else:
        raise ValueError(candidate)
    return head + body + tail


def candidate_out(candidate):
    return {"A": "c", "B": "c", "C": "e2", "D": "c2", "E": "c2"}[candidate]


def input_node(candidate):
    return "e" if candidate == "B" else ("b1" if candidate == "E" else "b")


def dc_nodes(candidate):
    return {
        "A": ["b", "c", "e"],
        "B": ["b", "c", "e"],
        "C": ["b", "c", "e", "e2"],
        "D": ["b", "e", "b2", "x", "c2"],
        "E": ["b1", "e1", "b2", "c2", "e2"],
    }[candidate]


def dc_expr(candidate):
    nodes = dc_nodes(candidate)
    values = " ".join("v(" + node + ")" for node in nodes)
    return values + " i(vcc) @q1[ic] @q1[ib]" + (" @q2[ic] @q2[ib]" if candidate in ("C", "D", "E") else "")


def build(candidate, load=10000.0, measure="zin", input_ac=1.0):
    """Build a netlist with an isolated AC test source at the input node."""
    node = input_node(candidate)
    out = candidate_out(candidate)
    ac_node = "b1" if candidate == "E" else node
    # A 1 F capacitor is an AC short and a DC open; it preserves the bias.
    input_test = f"VTEST vt 0 DC 0 AC {input_ac:.12g}\nCTEST vt {ac_node} 1\n"
    lines = [
        f"* AM-02.2 candidate {candidate}, load={load:g}",
        "VCC vcc 0 DC 5",
        circuit(candidate, load).split("VCC vcc 0 DC 5\n", 1)[1].rstrip(),
        input_test.rstrip(),
        MODEL,
        ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27",
        ".control",
        "set num_threads=1",
        "op",
        f"print {dc_expr(candidate)}",
        "ac lin 1 31meg 31meg",
        f"let zin=-v({ac_node})/i(vtest)",
        "print real(zin) imag(zin) mag(zin) ph(zin)",
        "ac dec 60 1meg 100meg",
        f"wrdata {ROOT / 'results' / ('resp_' + candidate + '_' + str(int(load)) + '.txt')} frequency db(v({out})) ph(v({out}))",
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"



def build_zin(candidate, load=10000.0):
    """Use a 1 A AC current source into the input node; Zin = v(node) ohm."""
    node = input_node(candidate)
    body = circuit(candidate, load).split("VCC vcc 0 DC 5\n", 1)[1].rstrip()
    return "\n".join([
        f"* AM-02.2 candidate {candidate} Zin, load={load:g}",
        "VCC vcc 0 DC 5",
        body,
        f"IAC 0 {node} AC 1",
        MODEL,
        ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27",
        ".control",
        "set num_threads=1",
        "op",
        f"print {dc_expr(candidate)}",
        "ac lin 1 31meg 31meg",
        f"print real(v({node})) imag(v({node})) mag(v({node})) ph(v({node}))",
        "quit",
        ".endc",
        ".end",
    ]) + "\n"


def run_zin(candidate, load=10000.0, tag=None):
    tag = tag or f"zin_{candidate}_{int(load)}"
    cir = NETLISTS / (tag + ".cir")
    log = LOGS / (tag + ".log")
    cir.write_text(build_zin(candidate, load), encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError("Zin run failed: " + str(log))
    body = log.read_text(encoding="utf-8", errors="replace")
    rr = re.search(r"real\(v\(([^)]+)\)\)\s*=\s*([0-9.eE+-]+)", body)
    ii = re.search(r"imag\(v\(([^)]+)\)\)\s*=\s*([0-9.eE+-]+)", body)
    if not rr or not ii:
        raise RuntimeError("could not parse Zin from " + str(log))
    zr, zi = float(rr.group(2)), float(ii.group(2))
    z = complex(zr, zi)
    y = 1.0 / z
    cpar = y.imag / (2 * math.pi * 31e6)
    return {"candidate": candidate, "load_ohm": load, "zin_real_ohm": zr,
            "zin_imag_ohm": zi, "zin_mag_ohm": abs(z),
            "zin_phase_deg": math.degrees(math.atan2(zi, zr)),
            "parallel_c_pf": cpar * 1e12,
            "netlist": str(cir), "netlist_sha256": sha(cir),
            "log": str(log), "log_sha256": sha(log)}

def run(candidate, load=10000.0, tag=None):
    tag = tag or f"{candidate}_{int(load)}"
    cir = NETLISTS / f"{tag}.cir"
    log = LOGS / f"{tag}.log"
    cir.write_text(build(candidate, load), encoding="utf-8", newline="\n")
    with log.open("w", encoding="utf-8", errors="replace") as stream:
        proc = subprocess.run([str(EXE), "-b", str(cir)], cwd=RESULTS,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError("run failed: " + str(log))
    body = log.read_text(encoding="utf-8", errors="replace")
    real = re.search(r"real\(zin\)\s*=\s*([0-9.eE+-]+)", body)
    imag = re.search(r"imag\(zin\)\s*=\s*([0-9.eE+-]+)", body)
    if not real or not imag:
        raise RuntimeError("could not parse zin from " + str(log))
    zr, zi = float(real.group(1)), float(imag.group(1))
    z = complex(zr, zi)
    y = 1.0 / z
    cpar = y.imag / (2 * math.pi * 31e6)
    resp_path = ROOT / "results" / f"resp_{candidate}_{int(load)}.txt"
    response = np.loadtxt(resp_path)
    # wrdata repeats the frequency before every vector; the useful columns are 4 and 6.
    if response.ndim != 2 or response.shape[1] < 7:
        raise ValueError("unexpected wrdata shape: " + str(response.shape))
    return {
        "candidate": candidate,
        "load_ohm": load,
        "zin_real_ohm": zr,
        "zin_imag_ohm": zi,
        "zin_mag_ohm": abs(z),
        "zin_phase_deg": math.degrees(math.atan2(zi, zr)),
        "parallel_c_pf": cpar * 1e12,
        "response_file": str(resp_path),
        "response_frequency_mhz": response[:, 0] / 1e6,
        "response_gain_db": response[:, 4],
        "response_phase_deg": response[:, 6],
        "netlist": str(cir),
        "netlist_sha256": sha(cir),
        "log": str(log),
        "log_sha256": sha(log),
    }


def summarize_point(record):
    f = record["response_frequency_mhz"]
    g = record["response_gain_db"]
    i = int(np.argmin(np.abs(f - 31.0)))
    peak = int(np.argmax(g))
    return {
        "gain_31mhz_db": float(g[i]),
        "phase_31mhz_deg": float(record["response_phase_deg"][i]),
        "peak_gain_db": float(g[peak]),
        "peak_frequency_mhz": float(f[peak]),
        "zin_real_ohm": record["zin_real_ohm"],
        "zin_imag_ohm": record["zin_imag_ohm"],
        "parallel_c_pf": record["parallel_c_pf"],
    }
