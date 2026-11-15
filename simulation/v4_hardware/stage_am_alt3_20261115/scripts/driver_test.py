"""Test whether a driver stage closes the 4.4x antenna-current gap.

First result worth noting: with the matching network alone (no new active stage),
the simulation delivered 1.193 mA rms of antenna current -- exactly the 1.193 mA
rms matched-power ceiling computed analytically in requirement.py. Two independent
methods agreeing to three digits means the ceiling is real, not an artefact of the
analysis. The gap is therefore structural: more voltage swing is needed.

This script then measures real driver topologies. An earlier version of this file
had broken node names (a CE stage with its collector tied to the supply and its
emitter on the base node), which drew 100 mA of supply current and delivered
almost nothing. The topology here is a proper CE gain stage followed by an emitter
follower, with the DC operating point checked before any AC result is believed.

    tp3 --[CBUF]-- base of QCE
    QCE: collector -> RDC -> vcc, emitter -> RDE (+ bypass CDE) -> gnd
    QEF: base = QCE collector, collector = vcc, emitter -> REF -> gnd
    antenna driven from the QEF emitter through the series-resonant match
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

R_ANT = 13.824
L_TUNE_NH = 2957.2
C_ANT_PF = 8.9130

# name -> (rload_ce, rb1, rb2, rde, cde, ref, roiso)
VARIANTS = {
    "drv2_a": dict(rload=1000, rb1=33000, rb2=10000, rde=47, cde="100n", ref=100, roiso=0),
    "drv2_b": dict(rload=1000, rb1=33000, rb2=10000, rde=10, cde="100n", ref=47, roiso=0),
    "drv2_c": dict(rload=680,  rb1=22000, rb2=6800,  rde=10, cde="100n", ref=22, roiso=0),
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


def strip_fixture():
    s = BASE.read_text(encoding="utf-8")
    s = s.replace("RTEST v3 0 10000\n", "")
    s = s.replace("CTEST v3 0 5e-12\n", "")
    for pat in (r"^LTX .*\n", r"^RLTX .*\n", r"^CTX .*\n"):
        s = re.sub(pat, "", s, flags=re.M)
    return s


def driver_block(p):
    """CE gain stage + emitter follower, all nodes defined exactly once.

    CBUF already exists in the inherited chain (tp3 -> ob); it is not re-added
    here, the old follower is removed instead and the new base taps tx_drv.
    """
    return f"""
* === AM-ALT.3 driver: common-emitter gain stage + emitter follower ===
RDRVIN tx_drv drv_b 220
RDB1 vcc drv_b {p['rb1']}
RDB2 drv_b 0 {p['rb2']}
QCE drv_c drv_b drv_e 2N3904
RDC vcc drv_c {p['rload']}
RDE drv_e 0 {p['rde']}
CDE drv_e 0 {p['cde']}
* follower: base at the CE collector, emitter drives the antenna match
QEF vcc drv_c ef_e 2N3904
REF ef_e 0 {p['ref']}
"""


def antenna_block(tap):
    return (f"LTUNE {tap} ant_n1 {L_TUNE_NH:.4f}n\n"
            f"RANT ant_n1 ant_n2 {R_ANT:.6f}\n"
            f"CANT ant_n2 0 {C_ANT_PF:.6f}p\n")


def build(name, p, kind):
    s = strip_fixture()
    if kind == "ef_only":
        s = s.replace("ROISO tx_drv v3 1000", "ROISO tx_drv v3 0.001")
        s = s.replace(".control", antenna_block("v3") + ".control")
    else:
        # remove the old follower so only the new driver drives the antenna
        for pat in (r"^QOB .*\n", r"^ROBT .*\n", r"^ROBB .*\n", r"^ROE .*\n",
                    r"^COV3 .*\n", r"^ROISO .*\n"):
            s = re.sub(pat, "", s, flags=re.M)
        s = s.replace(".control", driver_block(p) + antenna_block("ef_e") + ".control")
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    s = re.sub(r"^save .*$",
               "save v(v1) v(tp3) v(drv_b) v(drv_c) v(drv_e) v(ef_e) i(ltune) i(vsup)",
               s, flags=re.M)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")


def op_check(name, p):
    """DC operating point of the driver, from the tail of the run."""
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    sel = t > t[-1] - 50e-6
    return {
        "v_b": float(np.mean(d["v(drv_b)"][sel])),
        "v_c": float(np.mean(d["v(drv_c)"][sel])),
        "v_e": float(np.mean(d["v(drv_e)"][sel])),
        "v_ef_e": float(np.mean(d["v(ef_e)"][sel])),
        "vce_ce": float(np.mean(d["v(drv_c)"][sel] - d["v(drv_e)"][sel])),
        "i_c_ma": float(np.mean((5 - d["v(drv_c)"][sel]) / p["rload"])) * 1e3,
    }


def plateau(t, y, high, dc=True):
    edges = np.flatnonzero(np.diff(high.astype(int))) + 1
    hi, lo = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if t[b] - t[a] < 3e-6:
            continue
        sel = (t > t[b] - 1.4e-6) & (t < t[b] - .4e-6)
        if not sel.any():
            continue
        seg = y[sel]
        seg = seg - np.mean(seg) if dc else seg
        (hi if high[(a + b) // 2] else lo).append(np.sqrt(np.mean(seg ** 2)))
    return (float(np.mean(hi)) if hi else np.nan, float(np.mean(lo)) if lo else np.nan)


def analyse(name):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    v1 = d["v(v1)"]
    thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
    high = v1 > thr
    iant = np.abs(d["i(ltune)"])
    edges = np.flatnonzero(np.diff(high.astype(int))) + 1
    hi, lo = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if t[b] - t[a] < 3e-6:
            continue
        sel = (t > t[b] - 1.4e-6) & (t < t[b] - .4e-6)
        if not sel.any():
            continue
        (hi if high[(a + b) // 2] else lo).append(np.max(iant[sel]))
    mh, ml = float(np.mean(hi)), float(np.mean(lo))
    ih, il = plateau(t, d["i(ltune)"], high)
    return {
        "i_ant_high_mA_rms": ih * 1e3,
        "i_ant_low_mA_rms": il * 1e3,
        "i_ant_high_peak_mA": mh * 1e3,
        "i_ant_low_peak_mA": ml * 1e3,
        "m_current": (mh - ml) / (mh + ml),
        "i_supply_mA": float(np.mean(d["i(vsup)"])) * -1e3,
    }


if __name__ == "__main__":
    out = {}
    for name, kind in (("drv2_ef_only", "ef_only"),
                       ("drv2_a", "driver"), ("drv2_b", "driver"),
                       ("drv2_c", "driver")):
        p = VARIANTS.get(name, VARIANTS["drv2_a"])
        build(name, p, kind)
        log = ROOT / "results" / f"{name}.log"
        with log.open("w") as fh:
            r = subprocess.run([str(NG), "-b", str(ROOT / "netlists" / f"{name}.cir")],
                               cwd=ROOT / "results", stdout=fh,
                               stderr=subprocess.STDOUT, timeout=7200)
        if r.returncode:
            print(name, "FAILED ->", log)
            continue
        m = analyse(name)
        if kind != "ef_only":
            m["op"] = op_check(name, p)
        out[name] = m
        extra = ""
        if kind != "ef_only":
            o = m["op"]
            extra = (f" | Vb={o['v_b']:.2f} Vc={o['v_c']:.2f} Ve={o['v_e']:.2f} "
                     f"VCE={o['vce_ce']:.2f} IC={o['i_c_ma']:.2f}mA")
        print(f"{name:14} I_ant {m['i_ant_high_mA_rms']:6.3f} mA rms  "
              f"peak {m['i_ant_high_peak_mA']:6.3f}/{m['i_ant_low_peak_mA']:6.3f}  "
              f"m={m['m_current']*100:5.1f}%  I_sup={m['i_supply_mA']:6.2f} mA{extra}")
    (ROOT / "results" / "driver_test.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "driver_test.json")
