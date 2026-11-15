"""Size the driver stage from the requirement, then measure it on the real chain.

Two design faults in the earlier attempts are fixed here, and both are the kind
that produce a plausible-looking report if you only read the AC numbers:

  1. Removing the old follower also removed its coupling capacitor COV3, so the RF
     from tp3 never reached the new stage -- every node after it sat at a constant
     DC value and the antenna current was exactly zero.
  2. A 22 ohm follower emitter resistor looked attractive for a low output
     impedance but drew 70 mA of quiescent current at 1.54 V, which alone exceeds
     the whole 0.5 W transmitter budget.

Follower bias is therefore set by the peak current the antenna needs, not by the
emitter resistor's AC value: the antenna wants 111 mV peak across 14.8 ohm, i.e.
7.5 mA peak, so the follower runs at ~7.7 mA through a 200 ohm emitter resistor.
Its low output impedance comes from the low base-source impedance of the driving
CE collector, not from a small REF.

    requirement: 5.30 mA rms antenna current at the measured m = 0.243
    follower bias 7.7 mA  ->  peak current capability 7.7 mA > 7.5 mA needed
    total driver current ~10 mA, keeping the TX inside its power budget
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
I_TARGET_RMS_MA = 5.30

VARIANTS = {
    # name: (RDC, RB1, RB2, RDE, REF)
    "drv4_200":  (1250, 40000, 10000, 150, 200),
    "drv4_150":  (1000, 40000, 10000, 120, 150),
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


def build(name, rdc, rb1, rb2, rde, ref):
    s = BASE.read_text(encoding="utf-8")
    s = s.replace("RTEST v3 0 10000\n", "")
    s = s.replace("CTEST v3 0 5e-12\n", "")
    for pat in (r"^LTX .*\n", r"^RLTX .*\n", r"^CTX .*\n",
                r"^CBUF .*\n", r"^QOB .*\n", r"^ROBT .*\n", r"^ROBB .*\n",
                r"^ROE .*\n", r"^COV3 .*\n", r"^ROISO .*\n"):
        s = re.sub(pat, "", s, flags=re.M)
    driver = f"""
* === AM-ALT.3 driver: CE gain stage + follower sized from the antenna current ===
* CDRV restores the RF path that was lost together with the old COV3
CDRV tp3 drv_b 10n
RDB1 vcc drv_b {rb1}
RDB2 drv_b 0 {rb2}
QCE drv_c drv_b drv_e 2N3904
RDC vcc drv_c {rdc}
RDE drv_e 0 {rde}
CDE drv_e 0 100n
* follower bias set by the 7.5 mA peak the antenna needs, not by REF's AC value
QEF vcc drv_c ef_e 2N3904
REF ef_e 0 {ref}
LTUNE ef_e ant_n1 {L_TUNE_NH:.4f}n
RANT ant_n1 ant_n2 {R_ANT:.6f}
CANT ant_n2 0 {C_ANT_PF:.6f}p
"""
    s = s.replace(".control", driver + ".control")
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    s = re.sub(r"^save .*$",
               "save v(v1) v(tp3) v(drv_b) v(drv_c) v(drv_e) v(ef_e) "
               "i(ltune) i(vsup)", s, flags=re.M)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")


def analyse(name, rdc, ref):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    v1 = d["v(v1)"]
    thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
    high = v1 > thr
    tail = t > t[-1] - 60e-6
    op = {
        "Vb": float(np.mean(d["v(drv_b)"][tail])),
        "Vc": float(np.mean(d["v(drv_c)"][tail])),
        "Ve": float(np.mean(d["v(drv_e)"][tail])),
        "VCE_ce": float(np.mean(d["v(drv_c)"][tail] - d["v(drv_e)"][tail])),
        "IC_ce_mA": float(np.mean((5 - d["v(drv_c)"][tail]) / rdc)) * 1e3,
        "Vef": float(np.mean(d["v(ef_e)"][tail])),
        "I_fol_mA": float(np.mean(d["v(ef_e)"][tail]) / ref) * 1e3,
    }
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
    mh = float(np.mean(hi)) if hi else float("nan")
    ml = float(np.mean(lo)) if lo else float("nan")
    steady = t > 1.0e-3
    return {
        "op": op,
        "i_ant_high_peak_mA": mh * 1e3,
        "i_ant_low_peak_mA": ml * 1e3,
        "m_current": (mh - ml) / (mh + ml) if mh == mh and ml == ml else float("nan"),
        "i_ant_rms_mA": float(np.sqrt(np.mean(d["i(ltune)"][steady] ** 2))) * 1e3,
        "i_supply_mA": float(np.mean(d["i(vsup)"])) * -1e3,
    }


if __name__ == "__main__":
    out = {}
    for name, (rdc, rb1, rb2, rde, ref) in VARIANTS.items():
        build(name, rdc, rb1, rb2, rde, ref)
        log = ROOT / "results" / f"{name}.log"
        with log.open("w") as fh:
            r = subprocess.run([str(NG), "-b", str(ROOT / "netlists" / f"{name}.cir")],
                               cwd=ROOT / "results", stdout=fh,
                               stderr=subprocess.STDOUT, timeout=7200)
        if r.returncode:
            print(name, "FAILED ->", log)
            continue
        m = analyse(name, rdc, ref)
        out[name] = {**m, "settings": dict(RDC=rdc, RB1=rb1, RB2=rb2, RDE=rde, REF=ref)}
        o = m["op"]
        print(f"{name}: DC  Vb={o['Vb']:.2f} Vc={o['Vc']:.2f} Ve={o['Ve']:.2f} "
              f"VCE={o['VCE_ce']:.2f} V IC={o['IC_ce_mA']:.2f} mA "
              f"I_follower={o['I_fol_mA']:.2f} mA")
        flag = " <-- SATURATED" if o["VCE_ce"] < 0.6 else ""
        print(f"        AC  I_ant {m['i_ant_rms_mA']:.3f} mA rms "
              f"(peak {m['i_ant_high_peak_mA']:.3f}/{m['i_ant_low_peak_mA']:.3f}), "
              f"m={m['m_current']*100:.1f}%, I_sup={m['i_supply_mA']:.1f} mA{flag}")
        print(f"        {m['i_ant_rms_mA']/I_TARGET_RMS_MA*100:.1f}% of the "
              f"{I_TARGET_RMS_MA:.2f} mA rms requirement")
    (ROOT / "results" / "driver_test4.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "driver_test4.json")
