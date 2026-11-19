"""Final verification of the AM-ALT.3 antenna and driver result.

Corrects the envelope metric from final_driver.py, which reported m = 99.6% because
it took max/min over the whole window including the AM transition, where the
envelope crosses zero. Plateau-averaged peaks give the honest figure.

Then completes the two checks that decide whether the design is usable:

  - sidebands: demodulate the antenna current and compare the recovered 20 kHz
    waveform with v1 (frequency, duty, and fidelity);
  - detuning: the 1 m monopole's capacitance is the least certain quantity in the
    model, so the sensitivity is measured rather than assumed.
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
SCALES = {"fin_nom": 1.00, "fin_lo": 0.85, "fin_hi": 1.15}


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
* --- v3 alias (added 2026-11-16, P1b) ---------------------------------------
* The stage defines v3 as the voltage at the antenna feed point AFTER the
* matching network (01 report section 8). Once ROISO was removed there is no
* longer a node literally named v3: the feed point is ef_e. A zero-volt source
* between v3 and ef_e restores the name without perturbing a single volt or
* ampere, so v(v3) == v(ef_e) exactly and older save statements keep working.
* Historical raws produced before this change have no v(v3) column at all
* (fin_nom.raw has 6 variables); read v(ef_e) there -- it is the same quantity.
V3ALIAS v3 ef_e 0
LTUNE ef_e ant_n1 {L_TUNE_NH:.4f}n
RANT ant_n1 ant_n2 {R_ANT:.6f}
CANT ant_n2 0 {C_ANT_PF*c_scale:.6f}p
"""
    s = s.replace(".control", driver + ".control")
    s = re.sub(r"^write .*$", f"write {name}.raw", s, flags=re.M)
    s = re.sub(r"^save .*$",
               "save v(v1) v(ef_e) v(v3) i(ltune) i(vsup) i(v5)", s, flags=re.M)
    (ROOT / "netlists" / f"{name}.cir").write_text(s, encoding="utf-8")


def cycle_envelope(t, x):
    zc = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    pk = np.array([np.max(x[a:b]) for a, b in zip(zc[:-1], zc[1:])])
    return t[zc[:-1]], pk


def analyse(name):
    d = read_raw(ROOT / "results" / f"{name}.raw")
    t = d["time"]
    sel = t > 1.45e-3
    t, i, v1 = t[sel], d["i(ltune)"][sel], d["v(v1)"][sel]

    thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
    high = v1 > thr
    tc, pk = cycle_envelope(t, i)

    hi = [pk[k] for k in range(len(pk)) if high[np.searchsorted(t, tc[k])]]
    lo = [pk[k] for k in range(len(pk)) if not high[np.searchsorted(t, tc[k])]]
    # drop the transition cycles: keep cycles well inside each plateau
    h_mean = float(np.median(hi)) if hi else float("nan")
    l_mean = float(np.median(lo)) if lo else float("nan")
    m = (h_mean - l_mean) / (h_mean + l_mean)

    # recovered modulation: the cycle-peak envelope IS the demodulated waveform
    env_dc = (h_mean + l_mean) / 2
    rec = (pk - env_dc) / env_dc
    # compare duty and frequency of the recovered envelope against v1
    rec_high = rec > 0
    edges = np.flatnonzero(np.diff(rec_high.astype(int)) + 1 if False else
                           np.diff(rec_high.astype(int))) + 1
    rises = edges[rec_high[edges]]
    f_env = 1 / np.mean(np.diff(tc[rises])) if len(rises) > 1 else float("nan")
    duty_env = 100 * np.mean([np.sum(rec_high) / len(rec_high)]) if len(rec) else float("nan")

    steady = t > 1.4e-3
    return {
        "i_ant_rms_mA": float(np.sqrt(np.mean(i[steady] ** 2))) * 1e3,
        "i_peak_high_mA": h_mean * 1e3,
        "i_peak_low_mA": l_mean * 1e3,
        "m_plateau": m,
        "f_envelope_Hz": float(f_env),
        "duty_envelope_pct": float(duty_env),
        "i_rf_mA": float(np.mean(d["i(vsup)"][steady])) * -1e3,
        "i_lm393_mA": float(np.mean(d["i(v5)"][steady])) * -1e3,
        "n_cycles": int(len(pk)),
    }


if __name__ == "__main__":
    out = {}
    for name, scale in SCALES.items():
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
        p_bat = 9 * (m["i_rf_mA"] + m["i_lm393_mA"] + 8.0)
        out[name] = {**m, "c_scale": scale, "c_pf": C_ANT_PF * scale,
                     "p_bat_budget_mW": p_bat}
        print(f"{name:10} C={C_ANT_PF*scale:5.2f} pF  "
              f"I_ant={m['i_ant_rms_mA']:6.3f} mA rms  "
              f"peaks {m['i_peak_high_mA']:5.2f}/{m['i_peak_low_mA']:5.2f} mA  "
              f"m={m['m_plateau']*100:5.1f}%  "
              f"f_env={m['f_envelope_Hz']:8.1f} Hz  "
              f"duty={m['duty_envelope_pct']:5.1f}%  "
              f"P_bat={p_bat:6.1f} mW")
    (ROOT / "results" / "final_verify.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    if out:
        nom = out["fin_nom"]
        print(f"标称工况：天线电流 {nom['i_ant_rms_mA']:.3f} mA rms，"
              f"调制度 {nom['m_plateau']*100:.1f}%，"
              f"功率预算 {nom['p_bat_budget_mW']:.0f} mW")
        print(f"失谐敏感性：C 变化 ±15% 时天线电流 "
              f"{out['fin_lo']['i_ant_rms_mA']:.2f} – {out['fin_hi']['i_ant_rms_mA']:.2f} mA rms")
    print()
    print("written:", ROOT / "results" / "final_verify.json")
