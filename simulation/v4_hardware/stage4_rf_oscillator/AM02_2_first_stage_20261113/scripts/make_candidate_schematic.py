# -*- coding: utf-8 -*-
"""Generate a readable topology card sheet for the five AM-02.2 candidates.

The netlists are the authoritative wiring. These cards show the signal flow,
transistor connections and bias values used in the comparison.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[1] / "figures" / "AM02_2_candidates.svg"
W, H = 2120, 1450
BG, INK, MUTED, GRID = "#ffffff", "#17212b", "#64727e", "#dce5eb"
WIRE, ACCENT, GREEN = "#174d73", "#b5481c", "#1f6b4f"


def t(x, y, s, size=15, color=INK, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(s)}</text>')


def line(x1, y1, x2, y2, color=WIRE, w=2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"/>'


def arrow(x1, y1, x2, y2, color=WIRE):
    return line(x1, y1, x2, y2, color) + f'<polygon points="{x2},{y2} {x2-9},{y2-4} {x2-9},{y2+4}" fill="{color}"/>'


def npn(x, y, ref):
    return "".join([
        line(x - 42, y, x - 18, y), line(x - 18, y - 26, x - 18, y + 26),
        line(x - 18, y - 10, x + 14, y - 44), line(x + 14, y - 44, x + 14, y - 68),
        line(x - 18, y + 10, x + 14, y + 44), line(x + 14, y + 44, x + 14, y + 68),
        f'<polygon points="{x+1},{y+24} {x+14},{y+41} {x+4},{y+44}" fill="{WIRE}"/>',
        t(x + 24, y - 5, ref, 16, INK, weight="700"),
        t(x - 28, y - 7, "B", 10, MUTED), t(x + 20, y - 55, "C", 10, MUTED),
        t(x + 20, y + 56, "E", 10, MUTED),
    ])


def rv(x, y, value, text_color=INK):
    return (line(x, y, x, y + 12) +
            f'<rect x="{x-8}" y="{y+12}" width="16" height="42" fill="{BG}" stroke="{INK}" stroke-width="1.8"/>' +
            line(x, y + 54, x, y + 66) + t(x + 12, y + 40, value, 12, text_color))


def card(x, y, title, subtitle, flow, values, color=WIRE):
    out = [f'<rect x="{x}" y="{y}" width="650" height="390" rx="10" fill="#ffffff" stroke="{GRID}" stroke-width="1.5"/>',
           t(x + 22, y + 35, title, 21, INK, weight="700"),
           t(x + 22, y + 60, subtitle, 13, MUTED),
           t(x + 22, y + 90, flow, 13, color, weight="600")]
    # A generic signal-flow rail and input/output blocks; detailed values below.
    out.append(arrow(x + 30, y + 142, x + 125, y + 142, color))
    out.append(t(x + 155, y + 130, "AM-01 OUT", 12, MUTED, "middle"))
    out.append(t(x + 155, y + 148, "100 pF 隔直后", 11, MUTED, "middle"))
    out.append(f'<circle cx="{x+125}" cy="{y+142}" r="4" fill="{color}"/>')
    return "".join(out) + t(x + 22, y + 340, values, 12, INK)


def main():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="100%" height="100%" fill="{BG}"/>',
         f'<rect x="24" y="22" width="{W-48}" height="{H-44}" fill="none" stroke="{GRID}" stroke-width="2"/>',
         t(52, 62, "AM-02.2  31 MHz 第一级候选拓扑", 30, INK, weight="700"),
         t(52, 92, "所有候选使用 2N3904、5 V 单电源；图中给出信号流与偏置值，正式接线以 netlists/ 为准。", 14, MUTED),
         t(2070, 62, "REV 0.1  /  2026-11-13", 13, MUTED, "end", "600")]
    # Card A
    x, y = 45, 125
    p.append(card(x, y, "A  共射极 CE", "2N3904；输入直接落在 Q1 基极",
                  "AM-01 OUT → Q1 B；Q1 C → 100 pF → 负载",
                  "R1/R2=33 kΩ/6.8 kΩ；RE1=100 Ω；RC1=1 kΩ；COUT=100 pF\n输入约 319−j299 Ω @31 MHz；|Z|≈438 Ω；等效并联 C≈8.0 pF"))
    p.append(npn(x + 420, y + 220, "Q1"))
    p.append(line(x + 125, y + 142, x + 378, y + 220))
    p.append(rv(x + 330, y + 100, "R1 33k"))
    p.append(rv(x + 330, y + 255, "R2 6.8k"))
    p.append(t(x + 480, y + 145, "RC1 1 kΩ → +5 V", 12))
    p.append(t(x + 480, y + 275, "RE1 100 Ω → GND", 12))
    p.append(t(x + 480, y + 305, "C1 100 pF → OUT", 12))
    # Card B
    x, y = 725, 125
    p.append(card(x, y, "B  共基极 CB", "输入落在 Q1 发射极；基极交流接地",
                  "AM-01 OUT → Q1 E；Q1 C → 100 pF → 负载",
                  "R1/R2=10 kΩ/10 kΩ；CB=100 nF；RE1=1 kΩ；RC1=1 kΩ\n输入约 17 Ω @31 MHz（极低）；|Z|≈17 Ω；不适合直接高阻接口", ACCENT))
    p.append(npn(x + 420, y + 220, "Q1"))
    p.append(line(x + 125, y + 142, x + 392, y + 300))
    p.append(t(x + 125, y + 115, "→ E（不是 B）", 12, ACCENT, weight="700"))
    p.append(t(x + 480, y + 145, "RC1 1 kΩ → +5 V", 12))
    p.append(t(x + 480, y + 275, "RE1 1 kΩ → GND", 12))
    p.append(t(x + 480, y + 305, "B 经 CB=100 nF 到地", 12))
    # Card C
    x, y = 45, 545
    p.append(card(x, y, "C  共射极 + 射极跟随器", "Q1 CE 提供电压增益；Q2 EF 提供输出驱动",
                  "AM-01 OUT → Q1 B；Q1 C → Q2 B；Q2 E → 100 pF → 负载",
                  "Q1：R1/R2=33k/6.8k，RE1=100Ω，RC1=1k；Q2：RE2=2.2k，集电极接 +5V\n输入仍由 Q1 CE 决定：约 202−j198Ω，|Z|≈282Ω，C≈12.7pF", ACCENT))
    p.append(npn(x + 300, y + 205, "Q1"))
    p.append(npn(x + 480, y + 205, "Q2 EF"))
    p.append(line(x + 125, y + 142, x + 258, y + 205))
    p.append(arrow(x + 320, y + 205, x + 425, y + 205, ACCENT))
    p.append(t(x + 395, y + 265, "RE2 2.2 kΩ", 12))
    p.append(t(x + 395, y + 285, "→ GND", 12))
    p.append(t(x + 500, y + 300, "输出从 E2 取", 12))
    # Card D
    x, y = 725, 545
    p.append(card(x, y, "D  共射—共基 Cascode（附加对照）", "Q1 低 Miller；Q2 共基极提高输出阻抗",
                  "AM-01 OUT → Q1 B；Q1 C → Q2 E；Q2 C → 100 pF → 负载",
                  "Q1：R1/R2=33k/10k，RE1=470Ω 并联 1nF；Q2：基极 10k/10k，CB2=100nF；RC1=1k\n输入约 −5−j225Ω，|Z|≈225Ω，等效 C≈22.8pF；有轻微负实部，需稳定性复核", ACCENT))
    p.append(npn(x + 300, y + 205, "Q1"))
    p.append(npn(x + 485, y + 205, "Q2 CB"))
    p.append(line(x + 125, y + 142, x + 258, y + 205))
    p.append(arrow(x + 320, y + 205, x + 430, y + 205, ACCENT))
    p.append(t(x + 395, y + 275, "Q2 基极 10k/10k", 12))
    p.append(t(x + 395, y + 295, "+ CB2 100 nF", 12))
    # Card E
    x, y = 45, 965
    p.append(card(x, y, "E  射极跟随器 + 共射极（附加对照）", "Q1 EF 先隔离输入；Q2 CE 提供增益",
                  "AM-01 OUT → Q1 B；Q1 E → 1 nF → Q2 B；Q2 C → 100 pF → 负载",
                  "Q1：100k/100k，RE1=2.2k；Q2：R3/R4=33k/6.8k，RE2=100Ω，RC1=1k\n输入约 −176−j1472Ω，|Z|≈1.48kΩ，C≈3.44pF；出现负实部，当前不能作为稳定候选", ACCENT))
    p.append(npn(x + 280, y + 205, "Q1 EF"))
    p.append(npn(x + 465, y + 205, "Q2 CE"))
    p.append(line(x + 125, y + 142, x + 238, y + 205))
    p.append(arrow(x + 300, y + 205, x + 415, y + 205, ACCENT))
    p.append(t(x + 335, y + 260, "1 nF 耦合", 12))
    p.append(t(x + 520, y + 300, "输出从 Q2 C 取", 12))
    # Footer note
    p.append(t(52, 1410, "判据：A/C 为正实部输入；B 为 17 Ω 强加载；D 有轻微负实部；E 有明显负实部，暂不作为稳定候选。详细数据见 candidates.json。", 13, MUTED))
    p.append("</svg>")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(p), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
