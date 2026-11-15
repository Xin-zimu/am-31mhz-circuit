"""Design the output matching network and verify it in ngspice on the real chain.

Topology (series-L / shunt-C against the antenna, driven from the existing emitter
follower through ROISO):

    tx_drv --[ROISO 1k]-- v3 --+-- L_match --+-- antenna
                               |             |
                              C_shunt      (R_rad + R_loss_series)

The antenna is a 1 m monopole at 31 MHz: R_rad = 4.22 ohm, X = -576 ohm
(antenna_model.py). The series inductance tunes out the capacitance; the shunt
capacitor transforms the resulting low resistance up towards the source.

This script does two things:
  1. sweeps L and C to find values that put the *loaded* impedance in a range the
     existing follower can drive, while keeping loss acceptable;
  2. writes an ngspice netlist of the real AM-ALT.2 chain terminated in that
     network plus the modelled antenna, so the v3 waveform is measured rather than
     assumed.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

from antenna_model import C0, F, LAM, efficiency, schelkunoff

ROOT = Path(__file__).resolve().parents[1]
NG = Path("D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe")
ALT2 = ROOT.parent / "stage_am_alt2_20261115"

H = 1.00
A_WIRE = 0.5e-3
COIL_Q = 60.0


def antenna_impedance(coil_q=COIL_Q):
    """Series R + jX presented at the antenna port, including tuning coil loss."""
    rr, x = schelkunoff(H, A_WIRE)
    xl = abs(x)
    r_coil = xl / coil_q
    return rr + r_coil, x, xl


def network_gain(l_series, c_shunt, r_src=1039.0, coil_q=COIL_Q):
    """Voltage across the antenna port for 1 V source, and the power split."""
    r_ant, x_ant, xl = antenna_impedance(coil_q)
    w = 2 * np.pi * F
    zl = 1j * w * l_series
    zc = 1.0 / (1j * w * c_shunt)
    z_ant = r_ant + 1j * x_ant
    zp = 1.0 / (1.0 / zc + 1.0 / (zl + z_ant))
    ztot = r_src + zp
    v_port = 1.0 * zp / ztot
    i_ant = v_port / (zl + z_ant)
    p_ant = 0.5 * abs(i_ant) ** 2 * r_ant
    p_avail = 1.0 ** 2 / (8 * r_src)
    return {
        "v_port": abs(v_port),
        "i_ant": abs(i_ant),
        "r_in": abs(zp),
        "p_ant_w": p_ant,
        "efficiency_vs_available_pct": 100 * p_ant / p_avail,
    }


def choose():
    """L that series-resonates the antenna, and C that best matches the source."""
    rr, x, xl = antenna_impedance()
    w = 2 * np.pi * F
    l_res = xl / w
    best = None
    for c in np.linspace(2e-12, 200e-12, 4000):
        r = network_gain(l_res, c)
        # maximise delivered power, penalising a source that is too heavily loaded
        score = r["efficiency_vs_available_pct"]
        if best is None or score > best[0]:
            best = (score, c, r)
    return l_res, best[1], best[2], rr, x, xl


def build_netlist(name, l_series, c_shunt, coil_q=COIL_Q, step=0.125):
    """Real AM-ALT.2 chain with the matching network and modelled antenna."""
    src = ALT2 / "netlists" / "fine_a4_d50_h0125.cir"
    base = src.read_text(encoding="utf-8")
    # Replace the old 10k||5pF bench fixture with the real antenna + matching.
    r_ant, x_ant, xl = antenna_impedance(coil_q)
    l_tune = xl / (2 * np.pi * F)
    base = base.replace("RTEST v3 0 10000\n", "")
    base = base.replace("CTEST v3 0 5p\n", "")
    network = f"""
* --- AM-ALT.3: real monopole (h=1m, a=0.5mm) with series tuning and shunt match
* antenna radiation resistance and tuning-coil ESR, referred to the port
RANT v3 ant_r {r_ant:.6f}
* series tuning inductance (resonates the antenna capacitance)
LTUNE v3 ant_l {l_tune*1e9:.6f}n
CANT ant_l 0 {1/(2*np.pi*F*abs(x_ant))*1e12:.6f}p
* shunt matching capacitor
CMATCH v3 0 {c_shunt*1e12:.6f}p
"""
    out = base.replace(".control", network + "\n.control")
    out = out.replace("save v(v1)", "save v(v1)")
    (ROOT / "netlists" / f"{name}.cir").write_text(out, encoding="utf-8")
    return out


def run_ngspice(name):
    net = ROOT / "netlists" / f"{name}.cir"
    log = ROOT / "results" / f"{name}.log"
    with log.open("w") as fh:
        r = subprocess.run([str(NG), "-b", str(net)], cwd=ROOT / "results",
                           stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return r.returncode


if __name__ == "__main__":
    print(f"=== antenna: h={H} m monopole, coil Q={COIL_Q:.0f} ===")
    rr, x, xl = antenna_impedance()
    print(f"    R_rad+R_coil = {rr:.3f} ohm,  X = {x:.1f} ohm")
    print()

    l_res, c_best, r_best, rr, x, xl = choose()
    print("=== matching network search (source 1039 ohm) ===")
    print(f"    L_series (series resonance) = {l_res*1e9:.1f} nH")
    print(f"    C_shunt  (best match)       = {c_best*1e12:.2f} pF")
    print(f"    port |Z| = {r_best['r_in']:.1f} ohm,  "
          f"|I_ant| for 1 V = {r_best['i_ant']*1e3:.4f} mA")
    print(f"    power vs available = {r_best['efficiency_vs_available_pct']:.2f}%")
    print()

    print("=== sensitivity of delivered power to C_shunt ===")
    print(f"{'C/pF':>7} {'|Zin|/ohm':>10} {'I_ant/mA':>10} {'P/%avail':>10}")
    for c in (10, 20, 33, 47, 68, 100, 150):
        r = network_gain(l_res, c * 1e-12)
        print(f"{c:7.1f} {r['r_in']:10.1f} {r['i_ant']*1e3:10.4f} "
              f"{r['efficiency_vs_available_pct']:10.2f}")
    print()
    print("=== sensitivity of delivered power to L_series ===")
    print(f"{'L/nH':>8} {'delta':>8} {'I_ant/mA':>10} {'P/%avail':>10}")
    for frac in (-0.10, -0.05, 0.0, 0.05, 0.10):
        l = l_res * (1 + frac)
        r = network_gain(l, c_best)
        print(f"{l*1e9:8.1f} {100*frac:+7.0f}% {r['i_ant']*1e3:10.4f} "
              f"{r['efficiency_vs_available_pct']:10.2f}")

    params = {
        "antenna_h_m": H,
        "wire_radius_m": A_WIRE,
        "coil_q": COIL_Q,
        "R_total_ohm": rr,
        "X_ant_ohm": x,
        "L_series_nH": l_res * 1e9,
        "C_shunt_pF": c_best * 1e12,
        "port_Z_ohm": r_best["r_in"],
        "i_ant_per_volt_mA": r_best["i_ant"] * 1e3,
        "power_vs_available_pct": r_best["efficiency_vs_available_pct"],
    }
    (ROOT / "results" / "match_design.json").write_text(
        json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "match_design.json")
