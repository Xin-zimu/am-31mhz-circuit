# -*- coding: utf-8 -*-
"""Generate a clean SVG schematic for the optimized AM-01 circuit."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[1] / "AM01_optimized_schematic.svg"
W, H = 2000, 1160
BG = "#ffffff"
INK = "#17212b"
WIRE = "#174d73"
MUTED = "#62717e"
ACCENT = "#b5481c"
GRID = "#d8e2ea"


def t(x, y, text, size=18, color=INK, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{escape(text)}</text>')


def line(x1, y1, x2, y2, color=WIRE, width=2.2):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}"/>')


def dot(x, y, color=WIRE, r=5):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def term(x, y, name, sub):
    return "".join([
        f'<circle cx="{x}" cy="{y}" r="7" fill="{BG}" stroke="{INK}" stroke-width="2"/>',
        t(x, y - 18, name, 16, INK, "middle", "700"),
        t(x, y + 32, sub, 13, MUTED, "middle"),
    ])


def res_h(x, y, value, ref, length=110):
    a = x + 18
    b = x + length - 18
    return "".join([
        line(x, y, a, y),
        f'<rect x="{a}" y="{y-12}" width="{b-a}" height="24" fill="{BG}" stroke="{INK}" stroke-width="2"/>',
        line(b, y, x + length, y),
        t((x + x + length) / 2, y - 20, ref, 13, MUTED, "middle", "700"),
        t((x + x + length) / 2, y + 31, value, 15, INK, "middle"),
    ])


def res_v(x, y, value, ref, length=115):
    a = y + 18
    b = y + length - 18
    return "".join([
        line(x, y, x, a),
        f'<rect x="{x-12}" y="{a}" width="24" height="{b-a}" fill="{BG}" stroke="{INK}" stroke-width="2"/>',
        line(x, b, x, y + length),
        t(x - 18, y + length / 2 - 5, ref, 13, MUTED, "end", "700"),
        t(x + 20, y + length / 2 + 12, value, 15, INK),
    ])


def cap_h(x, y, value, ref, length=100):
    cx = x + length / 2
    return "".join([
        line(x, y, cx - 7, y),
        line(cx - 7, y - 17, cx - 7, y + 17),
        line(cx + 7, y - 17, cx + 7, y + 17),
        line(cx + 7, y, x + length, y),
        t(cx, y - 27, ref, 13, MUTED, "middle", "700"),
        t(cx, y + 36, value, 15, INK, "middle"),
    ])


def cap_v(x, y, value, ref, length=90):
    cy = y + length / 2
    return "".join([
        line(x, y, x, cy - 7),
        line(x - 17, cy - 7, x + 17, cy - 7),
        line(x - 17, cy + 7, x + 17, cy + 7),
        line(x, cy + 7, x, y + length),
        t(x + 23, cy - 5, ref, 13, MUTED, "start", "700"),
        t(x + 23, cy + 20, value, 15, INK),
    ])


def npn(x, y, ref, note=""):
    out = [
        line(x - 50, y, x - 22, y),
        line(x - 22, y - 30, x - 22, y + 30),
        line(x - 22, y - 12, x + 18, y - 50),
        line(x + 18, y - 50, x + 18, y - 80),
        line(x - 22, y + 12, x + 18, y + 50),
        line(x + 18, y + 50, x + 18, y + 80),
        f'<polygon points="{x-1},{y+27} {x+17},{y+46} {x+5},{y+51}" fill="{WIRE}"/>',
        t(x - 38, y - 8, "B", 11, MUTED, "middle"),
        t(x + 32, y - 63, "C", 11, MUTED, "middle"),
        t(x + 32, y + 64, "E", 11, MUTED, "middle"),
        t(x + 35, y - 12, ref, 18, INK, "start", "700"),
        t(x + 35, y + 12, note, 13, MUTED),
    ]
    return "".join(out)


def ground(x, y, label=False):
    out = [
        line(x, y, x, y + 20),
        line(x - 24, y + 20, x + 24, y + 20),
        line(x - 16, y + 29, x + 16, y + 29),
        line(x - 8, y + 38, x + 8, y + 38),
    ]
    if label:
        out.append(t(x, y + 57, "GND", 12, MUTED, "middle"))
    return "".join(out)


def junction(x, y):
    return dot(x, y)


p = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    f'<rect width="100%" height="100%" fill="{BG}"/>',
    f'<rect x="26" y="24" width="{W-52}" height="{H-48}" fill="none" stroke="{GRID}" stroke-width="2"/>',
    t(58, 66, "AM-01  2N3904 双管调幅器 · 优化后原理图", 30, INK, weight="700"),
    t(58, 96, "31 MHz 载波 · 20 kHz 方波 · 单 5 V 供电 · 调制律与两种规定负载已验证", 16, MUTED),
    t(1500, 64, "REV 1.0  /  2026-11-13", 14, MUTED, "end", "600"),
    t(1500, 90, "RBB=62 kΩ   RE=1.2 kΩ", 15, ACCENT, "end", "700"),
]

# Power rails
p.append(line(220, 125, 1500, 125, WIRE, 3))
p.append(t(230, 113, "+5 V", 19, ACCENT, weight="700"))
p.append(line(220, 1030, 1520, 1030, WIRE, 3))
p.append(t(1520, 1058, "GND", 15, MUTED, "middle", "700"))

# Carrier input and Q1
yin = 410
p.append(term(140, yin, "J1  TP2", "31 MHz, 2 Vpp"))
p.append(line(147, yin, 210, yin))
p.append(res_h(210, yin, "2.2 kΩ", "R1", 150))
p.append(junction(360, yin))
p.append(line(360, yin, 360, 475))
p.append(res_v(360, 475, "10 Ω", "R2", 105))
p.append(ground(360, 580))
p.append(line(360, yin, 405, yin))
p.append(cap_h(405, yin, "1 nF C0G", "C1", 105))
p.append(line(510, yin, 560, yin))
p.append(junction(540, yin))

q1x, q1y = 610, 410
p.append(npn(q1x, q1y, "Q1", "2N3904"))
p.append(t(535, 465, "VBE≈0.68 V", 12, MUTED, "middle"))
p.append(t(535, 483, "ICQ≈0.425 mA", 12, MUTED, "middle"))

# Q1 bias
p.append(line(540, 125, 540, 245))
p.append(res_v(540, 245, "10 kΩ", "R3", 115))
p.append(line(540, 360, 540, yin))
p.append(junction(540, yin))
p.append(line(540, yin, 540, 500))
p.append(res_v(540, 500, "10 kΩ", "R4", 115))
p.append(ground(540, 615))

# Q1 collector load and output coupling
p.append(line(628, 330, 628, 255))
p.append(line(628, 255, 800, 255))
p.append(junction(800, 255))
p.append(line(800, 255, 800, 205))
p.append(res_v(800, 125, "1 kΩ", "R5", 80))
p.append(line(800, 255, 870, 255))
p.append(cap_h(870, 255, "100 pF C0G", "C5", 110))
p.append(line(980, 255, 1360, 255))
p.append(junction(1100, 255))
p.append(term(1420, 255, "J2  AM_OUT", "RF 测试点"))
p.append(line(1360, 255, 1413, 255))

# Output test loads (local grounds, not the main rail)
p.append(line(1100, 255, 1100, 315))
p.append(res_v(1100, 315, "2 kΩ", "RL", 110))
p.append(ground(1100, 425))
p.append(line(1220, 255, 1220, 315))
p.append(cap_v(1220, 315, "10 pF", "CL", 90))
p.append(ground(1220, 405))
p.append(junction(1220, 255))
p.append(t(1070, 485, "RL / CL：规定测试负载，不是必装 BOM", 12, MUTED))

# Q1 emitter to X and Q2 collector
p.append(line(628, 490, 628, 660))
p.append(junction(628, 660))
p.append(line(628, 660, 500, 660))
p.append(cap_v(500, 660, "1 nF C0G", "C2", 90))
p.append(ground(500, 750))
p.append(line(628, 660, 628, 740))
p.append(t(665, 650, "X", 17, ACCENT, "start", "700"))

# Q2
q2x, q2y = 610, 820
p.append(npn(q2x, q2y, "Q2", "2N3904"))
p.append(t(660, 860, "VCE≈1.17–1.48 V", 12, MUTED))

# Q2 emitter resistor
p.append(line(628, 900, 628, 930))
p.append(res_v(628, 930, "1.2 kΩ", "R6", 100))
p.append(t(675, 970, "IEQ≈0.43 mA", 12, MUTED))

# Q2 base node, bias and CB2
p.append(line(560, 820, 1470, 820))
p.append(junction(520, 820))
p.append(line(1470, 125, 1470, 520))
p.append(res_v(1470, 520, "22 kΩ", "R7", 115))
p.append(line(1470, 635, 1470, 820))
p.append(junction(1470, 820))
p.append(line(1470, 820, 1470, 870))
p.append(res_v(1470, 870, "6.8 kΩ", "R8", 120))
p.append(line(1470, 990, 1470, 1030))
p.append(line(520, 820, 520, 865))
p.append(cap_v(520, 865, "47 pF", "C6", 85))
p.append(ground(520, 950))

# Modulation input
ym = 820
p.append(term(140, ym, "J3  v1", "20 kHz, 0–4 Vpp"))
p.append(line(147, ym, 200, ym))
p.append(cap_h(200, ym, "100 nF", "C7", 105))
p.append(line(305, ym, 345, ym))
p.append(res_h(345, ym, "62 kΩ", "R9", 130))
p.append(line(475, ym, 560, ym))
p.append(t(490, 790, "调制注入", 12, ACCENT, "middle", "700"))
p.append(t(490, 860, "100 nF 隔直；周期平均由 R9 建立", 11, MUTED, "middle"))

# Decoupling
for x, value, ref in [(275, "100 nF", "C3"), (330, "10 µF", "C4")]:
    p.append(line(x, 125, x, 185))
    p.append(cap_v(x, 185, value, ref, 90))
    p.append(ground(x, 275))
p.append(t(302, 325, "就近去耦", 12, MUTED, "middle"))

# Notes box
p.append(f'<rect x="1570" y="150" width="370" height="370" rx="10" fill="#f7fafc" stroke="{GRID}" stroke-width="1.5"/>')
p.append(t(1592, 185, "验证条件与结果", 18, INK, weight="700"))
notes = [
    "载波：31 MHz / 2 Vpp",
    "调制：20 kHz，10–50% 占空比",
    "电源：5 V；本调制器约 4.3 mW",
    "负载：2 kΩ∥10 pF / 10 kΩ∥10 pF",
    "调制度：25.48% @ 4 Vpp, 50%",
    "1–4 Vpp 线性误差：≤2.49%",
    "Q1/Q2 VCE 最小值：>1.16 V",
    "周期稳态与60 ms冷启动一致",
]
for i, note in enumerate(notes):
    p.append(t(1592, 220 + 31 * i, "• " + note, 14, INK))

p.append(f'<rect x="1570" y="550" width="370" height="300" rx="10" fill="#fff7f0" stroke="#e5b08f" stroke-width="1.5"/>')
p.append(t(1592, 585, "系统接口结论", 18, ACCENT, weight="700"))
for i, note in enumerate([
    "本电路只完成调制律，不等于可直接替代 POLY(3)。",
    "输出约 0.058/0.034 Vpp，比 POLY 低 30.6 dB。",
    "直接接 50 Ω 时仅约 6.5 mVpp，不能驱动天线。",
    "AM-02 必须增加宽带缓冲/增益与 50 Ω 接口。",
    "若要求单级完成乘法与功率输出，AD835 可作备选，",
    "但需 ±5 V 双电源，静态电流 16–25 mA。",
]):
    p.append(t(1592, 620 + 31 * i, note, 14, INK))

p.append(t(58, 1100, "2N3904 引脚（onsemi 2N3904BU，TO-92）：1=E，2=B，3=C。关键变化：RBB 82 kΩ→62 kΩ；RE 470 Ω→1.2 kΩ；R1 10 kΩ→2.2 kΩ；R2 100 Ω→10 Ω；C1 100 pF→1 nF。", 13, MUTED))
p.append("</svg>")
OUT.write_text("\n".join(p), encoding="utf-8")
print(OUT)
