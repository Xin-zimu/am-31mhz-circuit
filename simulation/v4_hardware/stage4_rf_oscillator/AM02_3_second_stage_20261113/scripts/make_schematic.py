# -*- coding: utf-8 -*-
"""AM-02.3 schematic: the two surviving second-stage candidates (S3, S6).

Every wire is placed on an explicit grid point so that symbol leads and wires
meet exactly; the previous revision drifted by 10-20 px in the input network.
"""
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
W, H = 1560, 700
INK = "#1f2933"
THIN = "#52606d"
ACC = "#b23a48"


def txt(x, y, s, size=15, anchor="middle", weight="400", fill=INK):
    return (f'<text x="{x}" y="{y}" font-family="Consolas,Menlo,monospace" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{escape(s)}</text>')


def ln(x1, y1, x2, y2, w=1.6, color=INK):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{w}" stroke-linecap="round"/>')


def path(pts, w=1.6, color=INK):
    d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"/>'


def dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="3.4" fill="{INK}"/>'


def gnd(x, y, w=44):
    out = [ln(x, y, x, y + 10, 1.8)]
    for i, half in enumerate((w / 2, w / 3, w / 6)):
        out.append(ln(x - half, y + 10 + i * 6, x + half, y + 10 + i * 6, 2.4))
    return "".join(out)


def res_v(x, y1, y2, label, value, side=1):
    y0, y3 = min(y1, y2), max(y1, y2)
    span, n, amp = y3 - y0, 6, 7
    pts = [(x, y0)]
    for i in range(n):
        pts.append((x + (amp if i % 2 == 0 else -amp), y0 + span * (i + 1) / (n + 1)))
    pts.append((x, y3))
    out = [path(pts)]
    out.append(txt(x + side * 14, (y0 + y3) / 2 - 3, label, 15,
                   "start" if side > 0 else "end", "600"))
    out.append(txt(x + side * 14, (y0 + y3) / 2 + 15, value, 13,
                   "start" if side > 0 else "end", "400", THIN))
    return "".join(out)


def res_h(y, x1, x2, label, value):
    x0, x3 = min(x1, x2), max(x1, x2)
    span, n, amp = x3 - x0, 6, 7
    pts = [(x0, y)]
    for i in range(n):
        pts.append((x0 + span * (i + 1) / (n + 1), y + (amp if i % 2 == 0 else -amp)))
    pts.append((x3, y))
    out = [path(pts)]
    out.append(txt((x0 + x3) / 2, y - 32, label, 15, "middle", "600"))
    out.append(txt((x0 + x3) / 2, y - 16, value, 13, "middle", "400", THIN))
    return "".join(out)


def cap_v(x, y, label, value, side=1):
    out = [ln(x - 13, y - 4, x + 13, y - 4, 2.6), ln(x - 13, y + 4, x + 13, y + 4, 2.6)]
    out.append(ln(x, y - 18, x, y - 4))
    out.append(ln(x, y + 4, x, y + 18))
    out.append(txt(x + side * 18, y + 1, label, 15, "start" if side > 0 else "end", "600"))
    out.append(txt(x + side * 18, y + 18, value, 13, "start" if side > 0 else "end", "400", THIN))
    return "".join(out)


def cap_h(y, x, label, value):
    out = [ln(x - 4, y - 13, x - 4, y + 13, 2.6), ln(x + 4, y - 13, x + 4, y + 13, 2.6)]
    out.append(ln(x - 18, y, x - 4, y))
    out.append(ln(x + 4, y, x + 18, y))
    out.append(txt(x, y - 26, label, 15, "middle", "600"))
    out.append(txt(x, y + 32, value, 13, "middle", "400", THIN))
    return "".join(out)


def ind_v(x, y1, y2, label, value, side=1):
    y0, y3 = min(y1, y2), max(y1, y2)
    span = (y3 - y0) / 4.0
    r = span / 2.0
    out = []
    for i in range(4):
        cy = y0 + r + i * span
        out.append(f'<path d="M{x},{cy - r} A{r},{r} 0 0 1 {x},{cy + r}" fill="none" '
                   f'stroke="{INK}" stroke-width="1.9"/>')
    out.append(txt(x + side * 16, (y0 + y3) / 2 - 3, label, 15,
                   "start" if side > 0 else "end", "600"))
    out.append(txt(x + side * 16, (y0 + y3) / 2 + 15, value, 13,
                   "start" if side > 0 else "end", "400", THIN))
    return "".join(out)


def ind_h(y, x1, x2, label, value):
    x0, x3 = min(x1, x2), max(x1, x2)
    span = (x3 - x0) / 4.0
    r = span / 2.0
    out = []
    for i in range(4):
        cx = x0 + r + i * span
        out.append(f'<path d="M{cx - r},{y} A{r},{r} 0 0 1 {cx + r},{y}" fill="none" '
                   f'stroke="{INK}" stroke-width="1.9"/>')
    out.append(txt((x0 + x3) / 2, y - 24, label, 15, "middle", "600"))
    out.append(txt((x0 + x3) / 2, y + 34, value, 13, "middle", "400", THIN))
    return "".join(out)


def npn(x, y, ref, part="2N3904"):
    out = [f'<circle cx="{x}" cy="{y}" r="28" fill="#f8fafc" stroke="{INK}" stroke-width="2"/>']
    out.append(ln(x - 15, y - 10, x - 15, y + 10, 3.4))
    out.append(ln(x - 34, y, x - 15, y, 1.8))
    out.append(ln(x - 15, y - 6, x + 6, y - 20, 1.9))
    out.append(ln(x + 6, y - 20, x + 6, y - 34, 1.9))
    out.append(ln(x - 15, y + 6, x + 6, y + 20, 1.9))
    out.append(f'<path d="M{x + 4},{y + 16} l11,10 l-1,-11 z" fill="{INK}"/>')
    out.append(ln(x + 6, y + 20, x + 6, y + 34, 1.9))
    out.append(txt(x + 36, y - 4, ref, 15, "start", "700"))
    out.append(txt(x + 36, y + 14, part, 13, "start", "400", THIN))
    return "".join(out), (x - 34, y), (x + 6, y - 34), (x + 6, y + 34)


RAIL = 180


def header(ox, title, sub):
    g = [f'<rect x="{ox}" y="96" width="740" height="560" rx="14" fill="#fcfdfe" stroke="#d9e2ec"/>']
    g.append(txt(ox + 24, 128, title, 16, "start", "700"))
    g.append(txt(ox + 24, 150, sub, 12.5, "start", "400", THIN))
    g.append(ln(ox + 30, RAIL, ox + 710, RAIL, 2.6))
    g.append(dot(ox + 60, RAIL))
    g.append(txt(ox + 30, RAIL - 12, "+5 V", 15, "start", "700", ACC))
    return "".join(g)


def panel_s3(ox):
    g = [header(ox, "S3：共射 + 扼流圈负载 + 射随输出（无调谐，推荐）",
                "50 Ω：0.386 Vpp / m 26.0% / THD 1.08% / 163 mW　　2 kΩ：0.441 Vpp，稳定")]
    x1, y1 = ox + 200, 330
    t1, b1, c1, e1 = npn(x1, y1, "QA")
    g.append(t1)

    g.append(txt(ox + 26, 325, "来自方案 A", 13, "start", "600", ACC))
    g.append(ln(ox + 26, 330, ox + 86, 330))
    g.append(cap_h(330, ox + 104, "CIN2", "100n"))
    g.append(ln(ox + 122, 330, b1[0], 330))
    g.append(dot(ox + 140, 330))
    g.append(res_v(ox + 140, RAIL, 330, "R1", "2.7k", side=-1))
    g.append(dot(ox + 140, RAIL))
    g.append(res_v(ox + 140, 330, 470, "R2", "1.1k", side=-1))
    g.append(gnd(ox + 140, 470))

    g.append(ln(e1[0], e1[1], e1[0], 380))
    g.append(dot(e1[0], 380))
    g.append(res_v(e1[0], 380, 420, "RAX", "2"))
    g.append(ln(e1[0], 420, e1[0], 436))
    g.append(dot(e1[0], 436))
    g.append(res_v(e1[0], 436, 474, "REA", "100"))
    g.append(gnd(e1[0], 474))
    g.append(ln(e1[0], 436, e1[0] + 54, 436))
    g.append(cap_v(e1[0] + 54, 454, "CEA", "1n"))
    g.append(ln(e1[0] + 54, 472, e1[0] + 54, 486))
    g.append(gnd(e1[0] + 54, 486))

    g.append(ln(c1[0], c1[1], c1[0], 230))
    g.append(dot(c1[0], 230))
    g.append(ind_v(c1[0], RAIL, 230, "LRFC", "2.2µ", side=-1))

    x2, y2 = ox + 460, 330
    t2, b2, c2, e2 = npn(x2, y2, "QB")
    g.append(t2)
    g.append(ln(c1[0], 230, c1[0] + 140, 230))
    g.append(ln(c1[0] + 140, 230, c1[0] + 140, 330))
    g.append(ln(c1[0] + 140, 330, b2[0], 330))
    g.append(ln(c2[0], c2[1], c2[0], RAIL))
    g.append(dot(c2[0], RAIL))
    g.append(ln(e2[0], e2[1], e2[0], 396))
    g.append(dot(e2[0], 396))
    g.append(res_v(e2[0], 396, 446, "REB", "180"))
    g.append(gnd(e2[0], 446))

    g.append(ln(e2[0], 396, e2[0] + 60, 396))
    g.append(cap_h(396, e2[0] + 78, "COUT2", "100n"))
    g.append(ln(e2[0] + 96, 396, e2[0] + 140, 396))
    g.append(dot(e2[0] + 140, 396))
    g.append(txt(e2[0] + 150, 386, "输出", 14, "start", "600", ACC))
    g.append(res_v(e2[0] + 140, 396, 470, "RL", "50"))
    g.append(gnd(e2[0] + 140, 470))
    g.append(ln(e2[0] + 140, 396, e2[0] + 200, 396))
    g.append(ln(e2[0] + 200, 396, e2[0] + 200, 420))
    g.append(cap_v(e2[0] + 200, 438, "CL", "10p", side=-1))
    g.append(ln(e2[0] + 200, 456, e2[0] + 200, 470))
    g.append(gnd(e2[0] + 200, 470))
    return "".join(g)


def panel_s6(ox):
    g = [header(ox, "S6：共射 + 谐振集电极 + 电容抽头 + 输入 L 匹配",
                "50 Ω：0.574 Vpp / m 24.7% / THD 0.55% / 101 mW　　2 kΩ：起振，仅作对照")]
    xq, yq = ox + 400, 330
    tr, base, col, emi = npn(xq, yq, "QA")
    g.append(tr)

    g.append(txt(ox + 26, 325, "来自方案 A", 13, "start", "600", ACC))
    g.append(ln(ox + 26, 330, ox + 86, 330))
    g.append(cap_h(330, ox + 104, "CIN6", "10n"))
    g.append(ln(ox + 122, 330, ox + 170, 330))
    g.append(dot(ox + 150, 330))
    g.append(ln(ox + 150, 330, ox + 150, 364))
    g.append(cap_v(ox + 150, 382, "CM", "68p"))
    g.append(ln(ox + 150, 400, ox + 150, 414))
    g.append(gnd(ox + 150, 414))
    g.append(ind_h(330, ox + 170, ox + 230, "LM", "820n"))
    g.append(ln(ox + 230, 330, ox + 252, 330))
    g.append(res_h(330, ox + 252, ox + 292, "RSER", "10"))
    g.append(ln(ox + 292, 330, base[0], 330))
    g.append(dot(ox + 320, 330))
    g.append(res_v(ox + 320, RAIL, 330, "R1", "2.2k", side=-1))
    g.append(dot(ox + 320, RAIL))
    g.append(res_v(ox + 320, 330, 470, "R2", "1.1k", side=-1))
    g.append(gnd(ox + 320, 470))

    g.append(ln(emi[0], emi[1], emi[0], 380))
    g.append(dot(emi[0], 380))
    g.append(res_v(emi[0], 380, 420, "RAX", "8.2"))
    g.append(ln(emi[0], 420, emi[0], 440))
    g.append(dot(emi[0], 440))
    g.append(res_v(emi[0], 440, 478, "REA", "39"))
    g.append(gnd(emi[0], 478))
    g.append(ln(emi[0], 440, emi[0] - 56, 440))
    g.append(cap_v(emi[0] - 56, 458, "CEA", "1n", side=-1))
    g.append(ln(emi[0] - 56, 476, emi[0] - 56, 490))
    g.append(gnd(emi[0] - 56, 490))

    tx = col[0] + 88
    g.append(ln(col[0], col[1], col[0], 230))
    g.append(ln(col[0], 230, tx, 230))
    g.append(dot(col[0], 230))
    g.append(ind_v(tx, RAIL, 230, "LTANK", "470n"))
    g.append(dot(tx, RAIL))
    g.append(ln(tx, 230, tx, 286))
    g.append(cap_v(tx, 304, "CT1", "100p"))
    g.append(ln(tx, 322, tx, 400))
    g.append(dot(tx, 400))
    g.append(txt(tx + 6, 392, "输出", 14, "start", "600", ACC))
    g.append(ln(tx, 400, tx, 424))
    g.append(cap_v(tx, 442, "CT2", "56p", side=-1))
    g.append(ln(tx, 460, tx, 470))
    g.append(gnd(tx, 470))

    g.append(ln(tx, 400, tx + 90, 400))
    g.append(dot(tx + 90, 400))
    g.append(res_v(tx + 90, 400, 470, "RL", "50"))
    g.append(gnd(tx + 90, 470))
    g.append(ln(tx + 90, 400, tx + 150, 400))
    g.append(ln(tx + 150, 400, tx + 150, 424))
    g.append(cap_v(tx + 150, 442, "CL", "10p", side=1))
    g.append(ln(tx + 150, 460, tx + 150, 470))
    g.append(gnd(tx + 150, 470))
    return "".join(g)


def main():
    body = [f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    body.append(txt(W / 2, 48, "AM-02.3  第二级 31 MHz 射频功放：两个存活方案", 26, "middle", "700"))
    body.append(txt(W / 2, 76, "AM-01（冻结）→ 方案 A（冻结）→ 第二级 → 50 Ω ∥ 10 pF；VCC = 5 V，全部 2N3904",
                    15, "middle", "400", THIN))
    body.append(panel_s3(20))
    body.append(panel_s6(800))
    body.append(txt(W / 2, 684,
                    "两者都保住 25% 调制、THD<1.2%、功耗在 0.5 W 内；高包络只到 0.386 / 0.574 Vpp，"
                    "距 2.0 Vpp 差 14.3 / 10.9 dB → AM-02 判定不完成。", 15, "middle", "600"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">' + "".join(body) + "</svg>")
    out = ROOT / "AM02_3_schematic.svg"
    out.write_text(svg, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
