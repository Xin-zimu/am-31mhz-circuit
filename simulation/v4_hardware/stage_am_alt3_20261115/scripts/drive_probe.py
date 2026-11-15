"""Where does the drive current go? Measure every node in the output path.

The first antenna run produced only 0.08 mA of antenna current. The cause was a
modelling error in this stage's own netlist: the antenna branch contained
R_ant + L_tune but *not* the antenna capacitance, so instead of a series-resonant
13.8 ohm load the circuit presented 576 ohm. Fixed here: the short monopole's
series equivalent is R_rad + 1/(jwC), and L_tune resonates that capacitance.

    v3 --L_tune-- n1 --R_ant-- n2 --C_ant-- ground
    with wL = 1/(wC)  ->  Z_branch = R_ant = 13.824 ohm at 31 MHz

The probe then measures each node between modulator and antenna so any remaining
loss is attributed rather than guessed.
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
R_ANT = 13.824                 # R_rad 4.224 + tuning-coil ESR 9.6 (Q=60)
X_ANT = 576.0                  # |X| of the 1 m monopole at 31 MHz
L_TUNE_NH = X_ANT / (2 * np.pi * F) * 1e9
C_ANT_PF = 1e12 / (2 * np.pi * F * X_ANT)

VARIANTS = {
    "probe_stock":  dict(roiso=1000.0, roe=330.0),
    "probe_iso22":  dict(roiso=22.0,   roe=330.0),
    "probe_roe47":  dict(roiso=22.0,   roe=47.0),
    "probe_roe10":  dict(roiso=10.0,   roe=10.0),
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


def build(name, roiso, roe):
    s = BASE.read_text(encoding="utf-8")
    s = s.replace("RTEST v3 0 10000\n", "")
    s = s.replace("CTEST v3 0 5e-12\n", "")
    s = re.sub(r"^LTX .*\n", "", s, flags=re.M)
    s = re.sub(r"^RLTX .*\n", "", s, flags=re.M)
    s = re.sub(r"^CTX .*\n", "", s, flags=re.M)
    s = s.replace("ROISO tx_drv v3 1000",
                  f"ROISO tx_drv v3 {roiso:g}" if roiso > 0 else "ROISO tx_drv v3 0.001")
    s = s.replace("ROE oe 0 330", f"ROE oe 0 {roe:g}")
    antenna = (f"\n* AM-ALT.3 antenna: 1 m monopole, series equivalent R + C, tuned by L\n"
               f"* |X_ant| = {X_ANT:.1f} ohm -> C = {C_ANT_PF:.4f} pF, L = {L_TUNE_NH:.2f} nH\n"
               f"LTUNE v3 ant_n1 {L_TUNE_NH:.4f}n\n"
               f"RANT ant_n1 ant_n2 {R_ANT:.6f}\n"
               f"CANT ant_n2 0 {C_ANT_PF:.6f}p\n")
    s = s.replace(".control", antenna + ".control")
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    s = re.sub(r"^save .*$",
               "save v(v1) v(tp3) v(ob) v(oe) v(tx_drv) v(v3) i(ltune) i(vsup)",
               s, flags=re.M)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")
    return name


def rms_plateau(t, y, high):
    """RMS on the interior of each source plateau (DC removed per plateau)."""
    edges = np.flatnonzero(np.diff(high.astype(int))) + 1
    hi, lo = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if t[b] - t[a] < 3e-6:
            continue
        sel = (t > t[b] - 1.4e-6) & (t < t[b] - .4e-6)
        if not sel.any():
            continue
        seg = y[sel]
        seg = seg - np.mean(seg)          # remove the DC operating point
        (hi if high[(a + b) // 2] else lo).append(np.sqrt(np.mean(seg ** 2)))
    return (float(np.mean(hi)) if hi else np.nan,
            float(np.mean(lo)) if lo else np.nan)


def analyse(name):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    v1 = d["v(v1)"]
    thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
    high = v1 > thr
    out = {}
    for node in ("v(tp3)", "v(tx_drv)", "v(v3)"):
        h, l = rms_plateau(t, d[node], high)
        out[node] = {"high_rms_mV": h * 1e3, "low_rms_mV": l * 1e3}
    h, l = rms_plateau(t, d["i(ltune)"], high)
    out["i_ant"] = {"high_rms_mA": h * 1e3, "low_rms_mA": l * 1e3}
    if "i(vsup)" in d:
        out["i_supply_mean_mA"] = float(np.mean(d["i(vsup)"])) * -1e3
    return out


if __name__ == "__main__":
    print(f"antenna branch: R={R_ANT:.3f} ohm  L={L_TUNE_NH:.1f} nH  "
          f"C={C_ANT_PF:.3f} pF   (resonant at {F/1e6:.0f} MHz)")
    print()
    res = {}
    for name, kw in VARIANTS.items():
        build(name, **kw)
        log = ROOT / "results" / f"{name}.log"
        with log.open("w") as fh:
            r = subprocess.run([str(NG), "-b", str(ROOT / "netlists" / f"{name}.cir")],
                               cwd=ROOT / "results", stdout=fh,
                               stderr=subprocess.STDOUT, timeout=7200)
        if r.returncode:
            print(name, "FAILED, see", log)
            continue
        m = analyse(name)
        res[name] = {"settings": kw, **m}
        print(f"{name:14} ROISO={kw['roiso']:6.1f} ROE={kw['roe']:5.1f}  "
              f"tp3={m['v(tp3)']['high_rms_mV']:7.2f} mV  "
              f"v3={m['v(v3)']['high_rms_mV']:7.2f} mV  "
              f"I_ant={m['i_ant']['high_rms_mA']:7.3f} mA  "
              f"low {m['i_ant']['low_rms_mA']:7.3f} mA  "
              f"I_sup={m.get('i_supply_mean_mA', float('nan')):6.2f} mA")
    (ROOT / "results" / "drive_probe.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "drive_probe.json")
