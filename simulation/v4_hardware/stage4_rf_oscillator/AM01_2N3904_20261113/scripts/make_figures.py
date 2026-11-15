# -*- coding: utf-8 -*-
"""Generate dependency-free SVG figures from the verified data."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
INK = "#17212b"
MUTED = "#6b7a86"
GRID = "#dfe7ed"
COLORS = ["#b5481c", "#1f6b4f", "#245b8a"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, color=INK, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')


def axes(x, y, w, h, xlabel, ylabel, xmin, xmax, ymin, ymax, xticks, yticks):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="{GRID}"/>']
    for value in xticks:
        px = x + (value - xmin) / (xmax - xmin) * w
        out.append(f'<line x1="{px:.2f}" y1="{y}" x2="{px:.2f}" y2="{y+h}" stroke="{GRID}"/>')
        out.append(text(px, y + h + 20, f"{value:g}", 12, MUTED, "middle"))
    for value in yticks:
        py = y + h - (value - ymin) / (ymax - ymin) * h
        out.append(f'<line x1="{x}" y1="{py:.2f}" x2="{x+w}" y2="{py:.2f}" stroke="{GRID}"/>')
        out.append(text(x - 10, py + 4, f"{value:g}", 12, MUTED, "end"))
    out.append(text(x + w / 2, y + h + 45, xlabel, 13, INK, "middle", "600"))
    out.append(f'<text x="{x-52}" y="{y+h/2}" font-family="Segoe UI, Microsoft YaHei, sans-serif" '
               f'font-size="13" fill="{INK}" text-anchor="middle" font-weight="600" '
               f'transform="rotate(-90 {x-52} {y+h/2})">{esc(ylabel)}</text>')
    return "".join(out)


def polyline(points, color, width=2.4):
    p = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'


def figure_waveform():
    raw = ROOT / "AM01_optimized_verified_4v50.raw"
    data = L.read_raw(raw)
    t = data["time"]
    y = data["v(out)"]
    env = L.demodulate(t, y)
    mask = (t >= 75e-6) & (t <= 125e-6)
    ts = (t[mask] - 75e-6) * 1e6
    env_mv = 2 * env[mask] * 1e3
    # decimate to keep SVG compact
    step = max(1, len(ts) // 2200)
    ts, env_mv = ts[::step], env_mv[::step]

    W, H = 1260, 760
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           text(50, 45, "AM-01 优化后 4 Vpp / 50% 仿真波形（ngspice）", 24, INK, weight="700"),
           text(50, 72, "2 kΩ∥10 pF；高电平 57.70 mVpp，低电平 34.26 mVpp，调制度 25.48%", 14, MUTED)]
    # envelope panel
    x0, y0, w, h = 90, 105, 800, 380
    out.append(axes(x0, y0, w, h, "相对周期起点 / µs", "包络 / mVpp", 0, 50, 0, 70,
                    [0, 10, 20, 30, 40, 50], [0, 20, 40, 60, 70]))
    pts = [(x0 + a / 50 * w, y0 + h - b / 70 * h) for a, b in zip(ts, env_mv)]
    out.append(polyline(pts, COLORS[0], 2.6))
    out.append(text(x0 + 40, y0 + 40, "高电平 57.70 mVpp", 14, COLORS[0], weight="600"))
    out.append(text(x0 + 460, y0 + 210, "低电平 34.26 mVpp", 14, COLORS[0], weight="600"))

    # RF window panel
    x1, y1, w1, h1 = 90, 550, 800, 160
    out.append(axes(x1, y1, w1, h1, "相对窗口起点 / ns", "RF 输出 / mV", 0, 160, -40, 40,
                    [0, 40, 80, 120, 160], [-40, -20, 0, 20, 40]))
    for center, offset, color, label in [(90e-6, 0, COLORS[1], "高电平"),
                                         (112e-6, 0, COLORS[2], "低电平")]:
        m = (t >= center) & (t <= center + 160e-9)
        tr = (t[m] - center) * 1e9
        yr = y[m] * 1e3
        pts = [(x1 + a / 160 * w1, y1 + h1 - (b + 40) / 80 * h1) for a, b in zip(tr, yr)]
        out.append(polyline(pts, color, 1.8))
        out.append(text(x1 + w1 - 10, y1 + (38 if color == COLORS[1] else 58), label, 13, color, "end", "600"))

    # annotation box
    out.append(f'<rect x="925" y="105" width="290" height="590" rx="10" fill="#f7fafc" stroke="{GRID}"/>')
    out.append(text(945, 140, "判据", 18, INK, weight="700"))
    lines = ["调制度 25.48%（目标 25±2%）",
             "包络占空比 49.955%",
             "上升 10–90%：0.55 µs",
             "下降 90–10%：0.61 µs",
             "载波 THD ≤2.17%",
             "Q1/Q2 最小 VCE：1.05 V",
             "无削顶；供电约 4.27 mW",
             "",
             "注意：幅度仅为 POLY 的 2.9%，",
             "系统级必须增加 AM-02 增益级。"]
    for i, line in enumerate(lines):
        out.append(text(945, 175 + 29 * i, line, 13, INK))
    out.append("</svg>")
    (FIG / "AM01_waveform_4v50.svg").write_text("\n".join(out), encoding="utf-8")


def figure_linearity():
    matrix = json.loads((RES / "matrix_final.json").read_text(encoding="utf-8"))
    sweep = json.loads((RES / "rbb_sweep_final_interface.json").read_text(encoding="utf-8"))
    W, H = 1260, 650
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           text(50, 42, "AM-01 参数选择与幅度线性", 24, INK, weight="700"),
           text(50, 68, "左：注入电阻扫描；右：最终参数下三种占空比的包络阶跃（2 kΩ∥10 pF）", 14, MUTED)]
    # sweep
    x0, y0, w, h = 90, 110, 470, 420
    out.append(axes(x0, y0, w, h, "RBB / kΩ", "4 Vpp, 50% 调制度 / %", 20, 85, 0, 70,
                    [20, 30, 40, 50, 60, 70, 80], [0, 20, 40, 60]))
    # target band
    ytop = y0 + h - 27 / 70 * h
    ybot = y0 + h - 23 / 70 * h
    out.append(f'<rect x="{x0}" y="{ytop:.2f}" width="{w}" height="{ybot-ytop:.2f}" fill="#f6d9c7" opacity="0.65"/>')
    out.append(text(x0 + 8, ytop - 6, "25%±2% 目标带", 12, COLORS[0], weight="600"))
    pts = []
    for item in sorted(sweep["records"], key=lambda r: r["rbb_ohm"]):
        x = x0 + (item["rbb_ohm"] / 1e3 - 20) / 65 * w
        yy = y0 + h - item["modulation_index"] * 100 / 70 * h
        pts.append((x, yy))
    out.append(polyline(pts, COLORS[0], 2.4))
    for px, py in pts:
        out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.5" fill="{COLORS[0]}"/>')
    selected = next(r for r in sweep["records"] if r["rbb_ohm"] == 62000)
    sx = x0 + (62 - 20) / 65 * w
    sy = y0 + h - selected["modulation_index"] * 100 / 70 * h
    out.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="6" fill="#ffffff" stroke="{COLORS[0]}" stroke-width="3"/>')
    out.append(text(sx + 8, sy - 10, "选择 62 kΩ / 25.48%", 12, COLORS[0], weight="700"))

    # linearity
    x1, y1, w1, h1 = 700, 110, 470, 420
    out.append(axes(x1, y1, w1, h1, "输入方波幅度 / Vpp", "包络阶跃 / mVpp", 0, 4.3, 0, 26,
                    [1, 2, 3, 4], [0, 5, 10, 15, 20, 25]))
    for index, (duty, color) in enumerate(zip([10, 30, 50], COLORS)):
        rows = sorted([r for r in matrix["records"] if r["load_ohm"] == 2000
                       and abs(r["duty_pct"] - duty) < 1e-9], key=lambda r: r["amp_vpp"])
        pts = [(x1 + r["amp_vpp"] / 4.3 * w1,
                y1 + h1 - r["envelope_step_vpp"] * 1e3 / 26 * h1) for r in rows]
        out.append(polyline(pts, color, 2.4))
        for px, py in pts:
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.5" fill="{color}"/>')
        out.append(text(px + 10, py + (index - 1) * 16 + 4, f"{duty}%", 13, color, weight="700"))
    out.append(text(700, 610, "最大线性误差：10%→2.27%，30%→1.14%，50%→0.14%", 13, MUTED))
    out.append("</svg>")
    (FIG / "AM01_sweep_linearity.svg").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    figure_waveform()
    figure_linearity()
    print("figures written")
