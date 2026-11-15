"""Figures for AM-ALT.3: antenna current envelope, sensitivity, and drive path."""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "figures"


def read_raw(p):
    b = p.read_bytes()
    off = b.index(b"Binary:\n")
    h = b[:off].decode("latin1")
    nv = int(re.search(r"No\. Variables:\s+(\d+)", h)[1])
    n = int(re.search(r"No\. Points:\s+(\d+)", h)[1])
    names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+\s*$", h.rsplit("Variables:", 1)[1], re.M)
    a = np.frombuffer(b, dtype=np.float64, count=nv * n, offset=off + 8).reshape(n, nv)
    return dict(zip(names, a.T))


def fig_envelope():
    d = read_raw(RES / "fin_nom.raw")
    t = d["time"]
    sel = t > 1.80e-3
    t, i, v1 = t[sel], d["i(ltune)"][sel], d["v(v1)"][sel]
    zc = np.flatnonzero((i[:-1] < 0) & (i[1:] >= 0))
    tc = t[zc[:-1]]
    pk = np.array([np.max(i[a:b]) for a, b in zip(zc[:-1], zc[1:])])

    fig, ax = plt.subplots(3, 1, figsize=(10, 8), constrained_layout=True)
    ax[0].plot((t - t[0]) * 1e6, v1, lw=0.8)
    ax[0].set_ylabel("v1 (V)")
    ax[1].plot((t - t[0]) * 1e6, i * 1e3, lw=0.4)
    ax[1].set_ylabel("antenna current (mA)")
    ax[2].plot((tc - t[0]) * 1e6, pk * 1e3, lw=1.0)
    ax[2].set_ylabel("cycle peak (mA)")
    ax[2].set_xlabel("time (us)")
    for a in ax:
        a.grid(alpha=.25)
    fig.suptitle("AM-ALT.3 nominal: 1 m monopole, tuned match | antenna current "
                 "6.25 mA rms, m=22.5%")
    fig.savefig(FIG / "alt3_antenna_envelope.png", dpi=150)
    plt.close(fig)


def fig_sensitivity():
    v = json.loads((RES / "final_verify.json").read_text(encoding="utf-8"))
    names = ["fin_lo", "fin_nom", "fin_hi"]
    labels = [f"C={v[n]['c_pf']:.2f} pF" for n in names]
    cur = [v[n]["i_ant_rms_mA"] for n in names]
    m = [v[n]["m_plateau"] * 100 for n in names]

    fig, ax = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    b = ax[0].bar(labels, cur, color=["#c44", "#2a2", "#c44"])
    ax[0].axhline(5.30, ls="--", color="k", label="requirement 5.30 mA rms")
    ax[0].bar_label(b, fmt="%.2f")
    ax[0].set_ylabel("antenna current (mA rms)")
    ax[0].legend()
    ax[0].set_title("tuning sensitivity")
    ax[1].bar(labels, m, color="#48a")
    ax[1].bar_label(ax[1].containers[0], fmt="%.1f")
    ax[1].set_ylabel("modulation index (%)")
    ax[1].set_title("m stays ~constant; it is current that collapses")
    for a in ax:
        a.grid(alpha=.25, axis="y")
    fig.suptitle("AM-ALT.3: antenna capacitance is the dominant uncertainty")
    fig.savefig(FIG / "alt3_sensitivity.png", dpi=150)
    plt.close(fig)


def fig_model_check():
    """Show how far the sinusoidal-current formula drifts in the short limit."""
    from antenna import induced_emf_dipole, C0
    f = 31e6
    lam = C0 / f
    frac = np.array([0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.25])
    ratio = []
    for x in frac:
        R, _ = induced_emf_dipole(x * lam, 0.5e-3, f)
        ratio.append(R / (197.0 * x ** 2))
    fig, ax = plt.subplots(figsize=(7, 4.2), constrained_layout=True)
    ax.semilogx(frac, ratio, "o-")
    ax.axhline(1.0, ls="--", color="k", label="correct short-dipole limit")
    ax.set_xlabel("length / lambda")
    ax.set_ylabel("R_emf / [197 (L/lambda)^2]")
    ax.set_title("Why the sinusoidal-current formula cannot be used at 0.103 lambda")
    ax.grid(alpha=.3, which="both")
    ax.legend()
    ax.annotate("1 m monopole\n(0.103 lambda)", xy=(0.103, 0.10),
                xytext=(0.02, 0.55), arrowprops=dict(arrowstyle="->"))
    fig.savefig(FIG / "alt3_model_check.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_envelope()
    fig_sensitivity()
    fig_model_check()
    for p in sorted(FIG.glob("*.png")):
        print(p.name, p.stat().st_size // 1024, "kB")
