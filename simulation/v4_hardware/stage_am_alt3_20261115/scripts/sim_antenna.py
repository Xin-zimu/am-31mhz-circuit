"""ngspice verification of the AM-ALT.2 chain driving the real 1 m antenna.

Replaces the 10k||5pF bench fixture with a series-resonant model of the monopole:

    v3 ---[ R_ant ]---[ L_tune ]--- ground
           13.824 ohm   2957 nH      (resonates the -576 ohm antenna reactance at 31 MHz)

R_ant = R_rad (4.224) + tuning-coil ESR (9.6 at Q=60). The loaded Q is then
576/13.824 = 41.7, bandwidth 743 kHz, so the 20 kHz AM sidebands sit well inside --
this script confirms that in the time domain rather than by assertion.

Three drive topologies are compared, because the existing output interface has a
1 kohm series isolation resistor that dominates a 14 ohm load:

    a  existing   ROISO 1k      (as AM-ALT.2 left it)
    b  reduced    ROISO 100
    c  direct     ROISO 0 + series matching

The measured quantity is the antenna current, i.e. the actual radiating quantity.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NG = Path("D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe")
ALT2 = ROOT.parent / "stage_am_alt2_20261115"
BASE = ALT2 / "netlists" / "full_a4_d50.cir"

F = 31e6
R_ANT = 13.824
L_TUNE_NH = 2957.4

VARIANTS = {
    "alt3_iso1k": dict(roiso=1000.0),
    "alt3_iso100": dict(roiso=100.0),
    "alt3_iso22": dict(roiso=22.0),
}


def read_raw(p):
    b = p.read_bytes()
    off = b.index(b"Binary:\n")
    h = b[:off].decode("latin1")
    nv = int(re.search(r"No\. Variables:\s+(\d+)", h)[1])
    n = int(re.search(r"No\. Points:\s+(\d+)", h)[1])
    names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+\s*$", h.rsplit("Variables:", 1)[1], re.M)
    a = np.frombuffer(b, dtype=np.float64, count=nv * n, offset=off + 8).reshape(n, nv)
    return dict(zip(names, a.T))


def build(name, roiso):
    s = BASE.read_text(encoding="utf-8")
    # swap the bench fixture for the real antenna
    s = s.replace("RTEST v3 0 10000\n", "")
    s = s.replace("CTEST v3 0 5e-12\n", "")
    s = s.replace("ROISO tx_drv v3 1000",
                  f"ROISO tx_drv v3 {roiso:g}" if roiso > 0 else "ROISO tx_drv v3 0.001")
    # existing shunt tank at v3 is the AM-ALT.1 preselection; keep it but retune
    # its role: with a real antenna it would short the RF. Remove it here and
    # account for the fact explicitly in the report.
    s = re.sub(r"^LTX .*\n", "", s, flags=re.M)
    s = re.sub(r"^RLTX .*\n", "", s, flags=re.M)
    s = re.sub(r"^CTX .*\n", "", s, flags=re.M)
    antenna = (f"\n* === AM-ALT.3 real antenna: 1 m monopole, series resonant ===\n"
               f"RANT v3 ant_r {R_ANT:.6f}\n"
               f"LTUNE ant_r 0 {L_TUNE_NH:.4f}n\n")
    s = s.replace(".control", antenna + ".control")
    # the copied control block still writes the donor run's filename
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    # make sure the antenna current is saved
    s = s.replace("save v(v1)", "save i(ltune) v(v1)")
    if "i(ltune)" not in s:
        s = s.replace(".control\n", ".control\nsave i(ltune)\n", 1)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")
    return name


def measure(name):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    iant = d.get("i(ltune)")
    if iant is None:
        for k in d:
            if "ltune" in k:
                iant = d[k]
                break
    v1 = d["v(v1)"]
    thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
    high = v1 > thr
    # peak antenna current on each plateau, late in the plateau
    edges = np.flatnonzero(np.diff(high.astype(int))) + 1
    vals = {}
    for a, b in zip(edges[:-1], edges[1:]):
        if t[b] - t[a] < 3e-6:
            continue
        sel = (t > t[b] - 1.4e-6) & (t < t[b] - .4e-6)
        if not sel.any():
            continue
        key = "high" if high[(a + b) // 2] else "low"
        vals.setdefault(key, []).append(np.max(np.abs(iant[sel])))
    return {
        "i_ant_high_mA": float(np.mean(vals.get("high", [np.nan]))) * 1e3,
        "i_ant_low_mA": float(np.mean(vals.get("low", [np.nan]))) * 1e3,
        "v3_high_rms_V": float(np.sqrt(np.mean(d["v(v3)"][high] ** 2))),
    }


if __name__ == "__main__":
    out = {}
    for name, kw in VARIANTS.items():
        net = build(name, kw["roiso"])
        log = ROOT / "results" / f"{name}.log"
        with log.open("w") as fh:
            r = subprocess.run([str(NG), "-b", str(ROOT / "netlists" / f"{net}.cir")],
                               cwd=ROOT / "results", stdout=fh,
                               stderr=subprocess.STDOUT, timeout=7200)
        if r.returncode:
            print(name, "FAILED, see", log)
            continue
        m = measure(net)
        out[name] = {"roiso_ohm": kw["roiso"], **m}
        print(f"{name:14} ROISO={kw['roiso']:6.1f}  "
              f"I_ant high={m['i_ant_high_mA']:7.4f} mA  "
              f"low={m['i_ant_low_mA']:7.4f} mA")
    (ROOT / "results" / "ant_drive.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "ant_drive.json")
