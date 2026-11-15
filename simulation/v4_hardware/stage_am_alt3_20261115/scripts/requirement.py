"""What antenna current does 6 m actually require, and can this stage supply it?

Answers three separate questions with numbers instead of assumptions:

  1. Requirement: the antenna current needed to give the receive antenna enough
     open-circuit voltage for the S05 receiver to produce v2 >= 4 Vpp.
     The modulation index matters here: the S05 design point was measured at
     m = 0.5, while AM-ALT.2 delivers m = 0.243, so the detector output is
     correspondingly smaller and more input is needed.
  2. Supply: the maximum the AM-ALT.2 modulator plus emitter follower can deliver,
     computed as matched-power transfer, so it is a hard ceiling.
  3. Gap: the ratio between them, which is what decides whether a driver stage is
     needed at all.

Short-monopole relations match antenna_model.py.
"""
import json
from pathlib import Path

import numpy as np

from antenna_model import C0, F, LAM, efficiency, schelkunoff

H = 1.00
A_WIRE = 0.5e-3
DIST = 6.0
COIL_Q = 60.0
R_GROUND = 1.0

# S05-06 measured: 10 mV open-circuit peak at the RX terminals gives
# 4.7770 Vpp of v2 at m = 0.5. The envelope detector output scales with the
# envelope swing, i.e. with m, so the same receiver at m = 0.243 gives
# roughly 4.777 * 0.243/0.5 Vpp.
V2_PER_MV_AT_M05 = 4.7770 / 10.0        # Vpp per mV of open-circuit peak
M_S05 = 0.50
M_ALT2 = 0.2431                          # measured, 4 Vpp setting
V2_REQUIRED = 4.0                        # Vpp, course threshold

ROOT = Path(__file__).resolve().parents[1]


def v2_for_input(v_oc_mv, m):
    """Estimated v2 Vpp for a given open-circuit peak and modulation index."""
    return v_oc_mv * V2_PER_MV_AT_M05 * (m / M_S05)


def required_voc(m=M_ALT2, target=V2_REQUIRED):
    """Open-circuit peak needed at the RX antenna for the target v2."""
    return target / (V2_PER_MV_AT_M05 * (m / M_S05))


def radiated_power_needed(v_oc, h_tx=H, h_rx=H, r=DIST):
    h_eff_rx = h_rx / 2
    e = v_oc / h_eff_rx
    return e ** 2 * r ** 2 / 180.0, e


def current_for_power(p_rad, h=H):
    rr = 395.0 * (h / LAM) ** 2
    return np.sqrt(p_rad / rr), rr


def available_power(v_rms, r_src):
    return v_rms ** 2 / (8 * r_src)


def main():
    out = {}
    print("=" * 74)
    print("1. 需求：从 v2 >= 4 Vpp 反推天线电流")
    print("=" * 74)
    print(f"    S05 实测：10 mV 开路峰值 @ m=0.50 -> v2 = 4.777 Vpp")
    print(f"    -> 灵敏度 {V2_PER_MV_AT_M05*1e3:.1f} Vpp/V")
    print()
    print(f"    AM-ALT.2 实测调制度 m = {M_ALT2*100:.1f}%（S05 设计点为 50%）")
    print(f"    -> 同样 10 mV 输入，v2 只有 {v2_for_input(10, M_ALT2):.2f} Vpp（不足 4 Vpp）")
    v_oc = required_voc()
    print(f"    -> 达到 v2 = {V2_REQUIRED} Vpp 需要开路峰值 {v_oc:.1f} mV")
    print()
    p_need, e_need = radiated_power_needed(v_oc / 1e3)
    i_need, r_rad = current_for_power(p_need)
    print(f"    接收有效高度 h_eff = {H/2:.2f} m -> 需要场强 {e_need*1e3:.1f} mV/m")
    print(f"    需要辐射功率 {p_need*1e6:.0f} uW，R_rad = {r_rad:.3f} ohm")
    print(f"    -> 天线电流峰值 {i_need*1e3:.2f} mA，rms {i_need/np.sqrt(2)*1e3:.2f} mA")
    print()

    eff = efficiency(H, A_WIRE, COIL_Q, R_GROUND)
    print(f"    天线效率（线圈Q=60，地损耗{R_GROUND}Ω）= {eff['efficiency_pct']:.1f}%")
    p_port = p_need / (eff["efficiency_pct"] / 100)
    v_port = i_need / np.sqrt(2) * eff["R_total"]
    print(f"    -> 端口功率 {p_port*1e6:.0f} uW，端口电压 {v_port*1e3:.1f} mVrms"
          f"（R_total={eff['R_total']:.2f} ohm）")
    out["requirement"] = {
        "m_alt2": M_ALT2,
        "v_oc_needed_mV_peak": v_oc,
        "p_radiated_needed_uW": p_need * 1e6,
        "i_ant_needed_mA_peak": i_need * 1e3,
        "i_ant_needed_mA_rms": i_need / np.sqrt(2) * 1e3,
        "efficiency_pct": eff["efficiency_pct"],
        "p_port_needed_uW": p_port * 1e6,
        "v_port_needed_mV_rms": v_port * 1e3,
    }
    print()

    print("=" * 74)
    print("2. 供给：现有调制器+射随的硬上限（匹配功率传输）")
    print("=" * 74)
    v_tp3_rms = 50.0e-3
    print(f"    tp3 调制器输出 = {v_tp3_rms*1e3:.1f} mVrms（AM-ALT.2 实测 142 mVpp）")
    print(f"    QOB 射随输出电阻 ~39 ohm（33k/33k 基极分压）")
    print()
    rows = []
    for r_src in (39.0, 20.0, 14.8, 10.0):
        p_av = available_power(v_tp3_rms, r_src)
        i_max = np.sqrt(p_av / eff["R_total"])
        rows.append((r_src, p_av * 1e6, i_max * 1e3))
        print(f"    源阻抗 {r_src:5.1f} ohm -> 可用 {p_av*1e6:6.2f} uW"
              f" -> 天线电流上限 {i_max*1e3:5.3f} mA rms")
    p_best = available_power(v_tp3_rms, eff["R_total"])
    i_best = np.sqrt(p_best / eff["R_total"])
    print()
    print(f"    理论绝对上限（源阻抗匹配到 {eff['R_total']:.2f} ohm）："
          f"{i_best*1e3:.2f} mA rms")
    out["supply"] = {
        "v_tp3_rms_mV": v_tp3_rms * 1e3,
        "r_out_ohm": 39.0,
        "i_max_mA_rms_by_source_ohm": {str(r): i for r, _, i in rows},
        "i_absolute_ceiling_mA_rms": i_best * 1e3,
    }
    print()

    print("=" * 74)
    print("3. 缺口与结论")
    print("=" * 74)
    i_need_rms = i_need / np.sqrt(2)
    ratio = i_need_rms / i_best
    print(f"    需要 {i_need_rms*1e3:.2f} mA rms；现有绝对上限 {i_best*1e3:.2f} mA rms")
    print(f"    电流缺口 {ratio:.2f}x，功率缺口 {ratio**2:.1f}x")
    print()
    print(f"    即使把 ROISO 降到 0、射随输出电阻压到 {eff['R_total']:.1f} ohm 完美匹配，")
    print(f"    也只能到 {i_best*1e3:.2f} mA rms，仍差 {ratio:.1f} 倍。")
    print(f"    -> 需要驱动级提供约 {ratio:.1f}x 的电压摆幅与 mA 级电流。")
    print("    这是由需求反推的结论；没有预先假设必须加功放。")
    print()
    print("    同时暴露一个跨阶段接口问题：AM-ALT.2 的 m=24% 只有 S05 设计点")
    print("    （m=50%）的一半，接收端在同样场强下输出也约减半。AM-ALT.4 必须")
    print("    按实际 m 重新核算，不能直接沿用 10 mV 设计点。")
    out["gap"] = {
        "current_ratio": ratio,
        "power_ratio": ratio ** 2,
        "driver_voltage_gain_needed": ratio,
    }
    (ROOT / "results" / "requirement.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("written:", ROOT / "results" / "requirement.json")


if __name__ == "__main__":
    main()
