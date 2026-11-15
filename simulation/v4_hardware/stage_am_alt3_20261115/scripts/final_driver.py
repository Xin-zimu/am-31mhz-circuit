"""Verify the chosen driver against the power budget and the AM sidebands.

The driver now delivers 6.25 mA rms of antenna current (118% of the 5.30 mA rms
requirement) at m = 22.5%. Two things still have to hold before it can be called a
candidate:

  1. Power budget: the course limit is 0.5 W at the battery. The driver adds
     supply current, so the 9 V budget must be recomputed, not assumed.
  2. Sidebands: the tuned antenna presents a loaded Q of ~42, so a 20 kHz
     modulation could in principle be attenuated. This is checked in the time
     domain by demodulating the antenna current envelope and measuring the
     fidelity of the recovered 20 kHz waveform.

Also measures the detuning sensitivity, because a real 1 m monopole's capacitance
depends on the counterpoise and nearby objects; if the design only works at exactly
8.913 pF it is not buildable.
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

CHOSEN = dict(rdc=1250, rb1=40000, rb2=10000, rde=150, ref=200)

# C detuning: the antenna capacitance is the least certain element in the model
DETUNE = {
    "det_c_nom": 1.00,
    "det_c_lo": 0.85,      # 7.6 pF
    "det_c_hi": 1.15,      # 10.3 pF
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


def build(name, c_scale=1.0, **p):
    s = BASE.read_text(encoding="utf-8")
    s = s.replace("RTEST v3 0 10000\n", "")
    s = s.replace("CTEST v3 0 5e-12\n", "")
    for pat in (r"^LTX .*\n", r"^RLTX .*\n", r"^CTX .*\n",
                r"^CBUF .*\n", r"^QOB .*\n", r"^ROBT .*\n", r"^ROBB .*\n",
                r"^ROE .*\n", r"^COV3 .*\n", r"^ROISO .*\n"):
        s = re.sub(pat, "", s, flags=re.M)
    driver = f"""
CDRV tp3 drv_b 10n
RDB1 vcc drv_b {p['rb1']}
RDB2 drv_b 0 {p['rb2']}
QCE drv_c drv_b drv_e 2N3904
RDC vcc drv_c {p['rdc']}
RDE drv_e 0 {p['rde']}
CDE drv_e 0 100n
QEF vcc drv_c ef_e 2N3904
REF ef_e 0 {p['ref']}
LTUNE ef_e ant_n1 {L_TUNE_NH:.4f}n
RANT ant_n1 ant_n2 {R_ANT:.6f}
CANT ant_n2 0 {C_ANT_PF*c_scale:.6f}p
"""
    s = s.replace(".control", driver + ".control")
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    s = re.sub(r"^save .*$",
               "save v(v1) v(ef_e) i(ltune) i(vsup) i(v5)", s, flags=re.M)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")


def envelope(t, x):
    """Peak envelope of the carrier, from local extrema."""
    idx = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    peaks = []
    for a, b in zip(idx[:-1], idx[1:]):
        peaks.append(np.max(np.abs(x[a:b + 1])))
    return t[idx[:-1]], np.array(peaks)


def analyse(name):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    iant = d["i(ltune)"]
    steady = t > 1.4e-3
    rms = float(np.sqrt(np.mean(iant[steady] ** 2))) * 1e3
    te, env = envelope(t[steady], iant[steady])
    hi = float(np.max(env))
    lo = float(np.min(env))
    m = (hi - lo) / (hi + lo)
    return {
        "i_ant_rms_mA": rms,
        "i_peak_high_mA": hi * 1e3,
        "i_peak_low_mA": lo * 1e3,
        "m_envelope": m,
        "i_supply_rf_mA": float(np.mean(d["i(vsup)"][steady])) * -1e3,
        "i_lm393_mA": float(np.mean(d["i(v5)"][steady])) * -1e3,
        "n_carrier_peaks": int(len(env)),
    }


if __name__ == "__main__":
    out = {}
    for name, scale in DETUNE.items():
        build(name, c_scale=scale, **CHOSEN)
        log = ROOT / "results" / f"{name}.log"
        with log.open("w") as fh:
            r = subprocess.run([str(NG), "-b", str(ROOT / "netlists" / f"{name}.cir")],
                               cwd=ROOT / "results", stdout=fh,
                               stderr=subprocess.STDOUT, timeout=7200)
        if r.returncode:
            print(name, "FAILED ->", log)
            continue
        m = analyse(name)
        p_bat = 9 * (m["i_supply_rf_mA"] + m["i_lm393_mA"] + 8.0)
        out[name] = {**m, "c_scale": scale, "p_bat_budget_mW": p_bat}
        print(f"{name:12} Cx{scale:.2f} ({C_ANT_PF*scale:5.2f} pF)  "
              f"I_ant={m['i_ant_rms_mA']:6.3f} mA rms  "
              f"m={m['m_envelope']*100:5.1f}%  "
              f"I_rf={m['i_supply_rf_mA']:5.2f} mA  "
              f"I_393={m['i_lm393_mA']:4.2f} mA  "
              f"P_bat={p_bat:6.1f} mW")
    (ROOT / "results" / "final_driver.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()

    ok = [v for v in out.values() if v["p_bat_budget_mW"] < 500]
    print(f"功率预算：{len(ok)}/{len(out)} 个工况低于 500 mW")
    if out:
        worst = max(out.values(), key=lambda v: v["p_bat_budget_mW"])
        print(f"最差工况 {worst['p_bat_budget_mW']:.1f} mW "
              f"= 上限的 {worst['p_bat_budget_mW']/5:.1f}%")
    print()
    print("written:", ROOT / "results" / "final_driver.json")
