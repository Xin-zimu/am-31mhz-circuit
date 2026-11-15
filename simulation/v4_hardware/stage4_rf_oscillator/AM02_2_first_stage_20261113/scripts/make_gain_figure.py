# -*- coding: utf-8 -*-
"""Generate a compact gain-vs-frequency SVG for the five candidates."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = ROOT / "figures" / "AM02_2_gain_10k.svg"
COLORS = {"A": "#b5481c", "B": "#245b8a", "C": "#1f6b4f", "D": "#7a4c9d", "E": "#8a6a1f"}
NAMES = {"A": "A CE", "B": "B CB", "C": "C CE+EF", "D": "D cascode", "E": "E EF+CE"}


def text(x, y, s, size=14, color="#17212b", anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def main():
    W, H = 1350, 720
    x0, y0, w, h = 100, 95, 1050, 500
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             text(48, 42, "AM-02.2 候选第一级增益（10 kΩ∥10 pF）", 24, weight="700"),
             text(48, 68, "输入节点为 AM-01 COUT 后；31 MHz 由虚线标出。", 14, "#64727e"),
             f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#ffffff" stroke="#dce5eb"/>']
    # log-frequency x axis 1..100 MHz
    for fx, label in [(1, "1"), (10, "10"), (31, "31"), (100, "100")]:
        x = x0 + (np.log10(fx) - 0) / 2 * w
        parts.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0+h}" stroke="#e6edf2"/>')
        parts.append(text(x, y0 + h + 24, label, 12, "#64727e", "middle"))
    parts.append(text(x0 + w / 2, y0 + h + 48, "频率 / MHz（对数）", 13, "#17212b", "middle", "600"))
    for gy in (-20, -10, 0, 10, 20, 30, 40):
        y = y0 + h - (gy + 20) / 60 * h
        parts.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+w}" y2="{y:.1f}" stroke="#e6edf2"/>')
        parts.append(text(x0 - 12, y + 5, f"{gy}", 12, "#64727e", "end"))
    parts.append(f'<text x="{x0-62}" y="{y0+h/2}" font-family="Segoe UI, Microsoft YaHei, sans-serif" font-size="13" fill="#17212b" text-anchor="middle" font-weight="600" transform="rotate(-90 {x0-62} {y0+h/2})">电压增益 / dB</text>')
    x31 = x0 + np.log10(31) / 2 * w
    parts.append(f'<line x1="{x31:.1f}" y1="{y0}" x2="{x31:.1f}" y2="{y0+h}" stroke="#b5481c" stroke-dasharray="5,4"/>')
    parts.append(text(x31 + 6, y0 + 20, "31 MHz", 12, "#b5481c", weight="600"))
    for c in "ABCDE":
        path = RES / f"resp_{c}_10000.txt"
        d = np.loadtxt(path)
        f = d[:, 0] / 1e6
        g = d[:, 4]
        mask = (f >= 1) & (f <= 100)
        points = []
        for ff, gg in zip(f[mask], g[mask]):
            xx = x0 + np.log10(ff) / 2 * w
            yy = y0 + h - (gg + 20) / 60 * h
            points.append(f"{xx:.1f},{yy:.1f}")
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{COLORS[c]}" stroke-width="2.2"/>')
    # legend
    parts.append(f'<rect x="1180" y="105" width="140" height="220" rx="8" fill="#f7fafc" stroke="#dce5eb"/>')
    for i, c in enumerate("ABCDE"):
        y = 135 + 38 * i
        parts.append(f'<line x1="1198" y1="{y}" x2="1225" y2="{y}" stroke="{COLORS[c]}" stroke-width="3"/>')
        parts.append(text(1235, y + 5, NAMES[c], 13))
    parts.append(text(48, 690, "注意：A/B/E 的输入极点使 31 MHz 增益明显低于 1 MHz；D 为带内抬升型，不能用单点增益代替频响。", 13, "#64727e"))
    parts.append("</svg>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
