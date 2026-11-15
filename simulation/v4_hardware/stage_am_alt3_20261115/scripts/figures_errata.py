"""Figures for the AM-ALT.3 errata: link-budget correction and directivity bracket.

Reads results/link_budget_audit.json and results/measurement_design.json so the
figures cannot drift from the numbers. No circuit simulation is performed.
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

audit = json.loads((RES / "link_budget_audit.json").read_text(encoding="utf-8"))
meas = json.loads((RES / "measurement_design.json").read_text(encoding="utf-8"))


def fig_bracket():
    rows = audit["bracket_by_directivity"]["rows"]
    d = [r["directivity"] for r in rows]
    i = [r["I_rms_mA"] for r in rows]
    driver = audit["driver_margin"]["simulated_rms_mA"]
    ceiling = audit["gap"]["ceiling_mA_rms"]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(d, i, "o-", lw=2.2, ms=8, color="#1f4e79", label="所需天线电流（rms）")
    for x, y in zip(d, i):
        ax.annotate(f"{y:.2f} mA", (x, y), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=9, color="#1f4e79")

    ax.axhline(driver, color="#2e7d32", ls="--", lw=2,
               label=f"驱动级仿真 {driver:.2f} mA rms")
    ax.axhline(ceiling, color="#c62828", ls=":", lw=2,
               label=f"原输出级硬上限 {ceiling:.2f} mA rms")

    # shade between the curve endpoints only: that IS the requirement bracket
    ax.axhspan(min(i), max(i), color="#bbdefb", alpha=0.55, zorder=0)
    ax.annotate(f"所需区间\n{min(i):.2f}–{max(i):.2f} mA",
                (2.25, (min(i) + max(i)) / 2), ha="center", va="center",
                fontsize=9, color="#0d47a1")

    ax.set_xlabel("发射天线方向性 D（地平面质量）")
    ax.set_ylabel("天线电流 / mA rms")
    ax.set_title("所需天线电流随方向性变化，与驱动级供给能力对照")
    ax.set_xlim(1.4, 3.1)
    ax.set_ylim(0, 7.2)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.text(0.02, 0.02, "驱动级在整个 D 区间内均有余量（112%–167%）",
            transform=ax.transAxes, fontsize=9,
            bbox=dict(fc="#e8f5e9", ec="#2e7d32", alpha=0.9))
    fig.tight_layout()
    fig.savefig(FIG / "alt3_link_bracket.png", dpi=150)
    plt.close(fig)


def fig_correction():
    """Bar chart: the requirement under the three conventions."""
    pub = audit["published_reported_rms_mA"]
    own = audit["published_model_consistent_rms_mA"]
    cor = audit["corrected"]["I_rms_mA"]

    labels = ["主报告标称\n(5.30)", "主报告自身模型\n自洽 rms", "修正后\n(D=3)"]
    vals = [pub, own, cor]
    colors = ["#c62828", "#ef6c00", "#1f4e79"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6))

    bars = ax1.bar(labels, vals, color=colors, width=0.58)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.2f} mA",
                 ha="center", fontsize=10, fontweight="bold")
    ax1.axhline(audit["driver_margin"]["simulated_rms_mA"], color="#2e7d32",
                ls="--", lw=2, label="驱动级 6.25 mA rms")
    ax1.set_ylabel("天线电流 / mA rms")
    ax1.set_title("同一需求的三种口径")
    ax1.set_ylim(0, 8.2)
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.3)

    # error attribution
    att = audit["attribution"]
    names = ["缺陷A\nh_eff=h/2", "缺陷B\nrms再除√2", "净效应"]
    factors = [att["defect_A_h_eff"]["current_factor"],
               att["defect_B_peak_rms"]["current_factor"],
               att["net"]["overstatement_factor"]]
    cols = ["#c62828", "#1565c0", "#455a64"]
    b2 = ax2.bar(names, factors, color=cols, width=0.55)
    ax2.axhline(1.0, color="k", lw=1.2, ls=":")
    for b, v in zip(b2, factors):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.03, f"×{v:.3f}",
                 ha="center", fontsize=10, fontweight="bold")
    ax2.set_ylabel("对电流需求的倍率")
    ax2.set_title("两处约定错误的单项归因（净 √2）")
    ax2.set_ylim(0, 2.4)
    ax2.grid(axis="y", alpha=0.3)
    ax2.text(0.5, 0.06, "两项方向相反，几乎抵消；\n数字碰巧安全，但推导不可复现",
             transform=ax2.transAxes, ha="center", fontsize=9,
             bbox=dict(fc="#fff8e1", ec="#f9a825", alpha=0.95))

    fig.tight_layout()
    fig.savefig(FIG / "alt3_link_correction.png", dpi=150)
    plt.close(fig)


def fig_measurement():
    """Probe loading: what a 16 pF probe does to each candidate node."""
    rows = meas["probe_loading"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.4))

    # left: resonance shift when probing the antenna node
    c_model = 8.913
    c_probe = 16.0
    l_uh = meas["tuning_range"]["rows"][1]["L_required_uH"]
    cs = np.linspace(0, 20, 400)
    f = lambda c: 1 / (2 * np.pi * np.sqrt(l_uh * 1e-6 * (np.asarray(c) + c_model) * 1e-12)) / 1e6
    ax1.plot(cs, f(cs), lw=2, color="#c62828")
    ax1.axvline(0, color="#2e7d32", ls="--", lw=2, label="不接探头：31.0 MHz")
    ax1.axvline(c_probe, color="#c62828", ls=":", lw=2,
                label=f"16 pF 探头：{f(c_probe):.1f} MHz")
    ax1.plot([c_probe], [f(c_probe)], "o", ms=8, color="#c62828")
    ax1.set_xlabel("探头顶端附加电容 / pF")
    ax1.set_ylabel("串联谐振频率 / MHz")
    ax1.set_title("直接测天线节点：探头把谐振拉走 40%")
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=9)
    ax1.annotate("16 pF 相对 8.91 pF 天线\n是 +180% 的加载",
                 (c_probe, f(c_probe)), textcoords="offset points",
                 xytext=(-105, 45), fontsize=9, color="#c62828",
                 arrowprops=dict(arrowstyle="->", color="#c62828"))

    # right: error in L from the two-capacitor method
    scen = meas["l_measurement_scenarios"]
    names = ["带内 28–34 MHz\n(2.1 pF 步长)", "低频大电容\n(120 pF 步长)"]
    errs = [abs(s["error_budget"]["total_error_pct"]) for s in scen]
    bars = ax2.bar(names, errs, color=["#c62828", "#2e7d32"], width=0.5)
    for b, v in zip(bars, errs):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}%",
                 ha="center", fontsize=11, fontweight="bold")
    ax2.axhline(5.0, color="#f9a825", ls="--", lw=2, label="5% 目标线")
    ax2.set_ylabel("L 复原误差 / %")
    ax2.set_title("双电容法测 L：测试频率决定成败")
    ax2.set_ylim(0, 24)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    ax2.text(0.5, 0.72, "C ∝ 1/L：L 差 20%\n则 C 也差 20%，测量失去意义",
             transform=ax2.transAxes, ha="center", fontsize=9,
             bbox=dict(fc="#ffebee", ec="#c62828", alpha=0.95))

    fig.tight_layout()
    fig.savefig(FIG / "alt3_measurement_plan.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    fig_bracket()
    fig_correction()
    fig_measurement()
    for p in ("alt3_link_bracket.png", "alt3_link_correction.png",
              "alt3_measurement_plan.png"):
        f = FIG / p
        print(f"{p:34} {f.stat().st_size/1024:8.1f} kB")
