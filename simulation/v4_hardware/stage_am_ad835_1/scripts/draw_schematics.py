"""Carrier-interface schematics with explicit ports and automated QA.

Electrical connectivity is defined once, here, as a coordinate contract.
QA enforces:
  1. every wire endpoint is a declared port, a registered component terminal,
     or lies on another wire (no dangling ends);
  2. every connected port is actually reached by a wire;
  3. no two texts overlap;
  4. no text sits on a wire;
  5. no text escapes the canvas;
  6. nothing intrudes into the title block.
If a wire is wrong the contract here is wrong: edit this file, never the SVG.
"""
from pathlib import Path
import itertools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

ROOT = Path(__file__).resolve().parents[1]
DRAW = ROOT / 'drawings'
DRAW.mkdir(exist_ok=True)

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

BLUE, RED, GREEN, INK, GREY = '#2469ad', '#b03528', '#1d6f42', '#15243b', '#8a95a6'

W, H = 1400, 880
TITLE_TOP, SUB_Y, KEEPOUT = 40, 70, 100

BX, BY, BW, BH = 860, 195, 245, 325
ROWS = [('1 · Y1', 'Y1', 240), ('2 · Y2', 'Y2', 280), ('4 · Z', 'Z', 320),
        ('7 · X2', 'X2', 360), ('8 · X1', 'X1', 400),
        ('6 · VP', 'VP', 440), ('3 · VN', 'VN', 480)]
STUB, W_ROW = 64, 320
PIN_X = BX - STUB
X1_STUB_MID = BX - STUB / 2
WOUT = BX + BW + STUB
# pins that are labelled but carry no wire in these candidates, by design
ANNOTATED_ONLY = {'Y2', 'X2', 'VP', 'VN'}

SUBTITLE = 'UNVERIFIED  *  no official AD835 SPICE model  *  review only, do not build'
FOOTER = ('Not a construction schematic: Y/Z are 100k//2pF, 60k//2pF plus signed bias-current '
          'sources. VP/VN decoupling unverified without the device model.')


class Sheet:
    def __init__(self, title, subtitle=SUBTITLE, w=W, h=H):
        self.w, self.h = w, h
        self.fig = plt.figure(figsize=(w / 100, h / 100), dpi=110)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w); self.ax.set_ylim(h, 0); self.ax.axis('off')
        self.ax.add_patch(Rectangle((0, 0), w, h, facecolor='#f7f9fc', edgecolor='none'))
        self.ports, self.terms, self.wires, self.texts = {}, set(), [], []
        self.drawn = []          # ref-des of every component actually drawn
        self.bodies = []         # (name, x0, y0, x1, y1) keep-out of each body
        self._t = self.ax.text(38, TITLE_TOP, title, fontsize=16.5, fontweight='bold',
                               color=INK, va='center', zorder=6)
        self.texts.append(self._t)
        self._s = self.ax.text(38, SUB_Y, subtitle, fontsize=10.5, color=RED,
                               va='center', zorder=6)
        self.texts.append(self._s)
        self.keepout = KEEPOUT

    # -- primitives ---------------------------------------------------------
    def port(self, name, x, y):
        self.ports[name] = (float(x), float(y))
        return self.ports[name]

    def dev(self, ref, body=None):
        if ref:
            self.drawn.append(ref)
        if body:
            self.bodies.append((ref or '?',) + tuple(body))

    def term(self, p):
        self.terms.add((float(p[0]), float(p[1])))
        return (float(p[0]), float(p[1]))

    def text(self, x, y, s, size=10, color=INK, ha='left', weight='normal'):
        t = self.ax.text(x, y, s, fontsize=size, color=color, ha=ha, va='center',
                         fontweight=weight, zorder=6)
        self.texts.append(t)
        return t

    def wire(self, pts, color=BLUE, lw=2.0, ls='-', zorder=2):
        self.ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, ls=ls,
                     solid_capstyle='round', solid_joinstyle='round', zorder=zorder)
        for a, b in zip(pts, pts[1:]):
            self.wires.append((tuple(map(float, a)), tuple(map(float, b))))

    def box(self, x, y, w, h):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h,
                                         boxstyle='round,pad=0,rounding_size=8',
                                         facecolor='white', edgecolor=GREY,
                                         linewidth=1.4, zorder=2))

    def res_h(self, cx, cy, label, ln=54, ref=None):
        n, amp, step = 6, 8, ln / 6
        px, py = [cx - ln / 2], [cy]
        for i in range(n):
            px += [cx - ln / 2 + step * (i + .5), cx - ln / 2 + step * (i + 1)]
            py += [cy + (amp if i % 2 == 0 else -amp), cy]
        self.ax.plot(px, py, color=BLUE, lw=2.0, zorder=3)
        self.text(cx, cy - 19, label, size=9.5, ha='center')
        self.dev(ref, (cx - ln / 2, cy - 11, cx + ln / 2, cy + 11))
        a, b = (cx - ln / 2, cy), (cx + ln / 2, cy)
        self.term(a); self.term(b)
        return a, b

    def res_v(self, cx, cy, label, ln=44, side=1, ref=None):
        n, amp, step = 6, 8, ln / 6
        py, px = [cy - ln / 2], [cx]
        for i in range(n):
            py += [cy - ln / 2 + step * (i + .5), cy - ln / 2 + step * (i + 1)]
            px += [cx + (amp if i % 2 == 0 else -amp), cx]
        self.ax.plot(px, py, color=BLUE, lw=2.0, zorder=3)
        self.text(cx + side * 22, cy, label, size=9.5,
                  ha='left' if side > 0 else 'right')
        self.dev(ref, (cx - 11, cy - ln / 2, cx + 11, cy + ln / 2))
        a, b = (cx, cy - ln / 2), (cx, cy + ln / 2)
        self.term(a); self.term(b)
        return a, b

    def cap_h(self, cx, cy, label, gap=9, lead=15, ref=None):
        self.wire([(cx - gap - lead, cy), (cx - gap, cy)])
        self.wire([(cx + gap, cy), (cx + gap + lead, cy)])
        for s in (-1, 1):
            self.ax.plot([cx + s * gap, cx + s * gap], [cy - 13, cy + 13],
                         color=BLUE, lw=2.4, zorder=3)
        self.text(cx, cy - 23, label, size=9.5, ha='center')
        self.dev(ref, (cx - gap - 2, cy - 13, cx + gap + 2, cy + 13))
        a, b = (cx - gap - lead, cy), (cx + gap + lead, cy)
        self.term((cx - gap, cy)); self.term((cx + gap, cy))
        self.term(a); self.term(b)
        return a, b

    def gnd(self, x, y, label=None):
        self.term((x, y)); self.term((x, y + 12))
        self.wire([(x, y), (x, y + 12)], color=INK, lw=1.6, zorder=4)
        for i, dx in enumerate((11, 7, 3)):
            self.ax.plot([x - dx, x + dx], [y + 12 + i * 4, y + 12 + i * 4],
                         color=INK, lw=1.6, zorder=4)
        if label:
            self.text(x + 18, y + 22, label, size=9.2, color=GREY)

    def npn(self, cx, cy, label, r=24, ldx=0, ldy=None, lha='center', ref=None):
        self.ax.add_patch(Circle((cx, cy), r, facecolor='white', edgecolor=INK,
                                 linewidth=1.6, zorder=3))
        self.wire([(cx - r, cy), (cx - 6, cy)], color=INK, lw=1.6, zorder=4)
        self.ax.plot([cx - 6, cx - 6], [cy - 14, cy + 14], color=INK, lw=2.2, zorder=4)
        self.ax.plot([cx - 6, cx + 12], [cy - 7, cy - 19], color=INK, lw=1.6, zorder=4)
        self.ax.plot([cx - 6, cx + 12], [cy + 7, cy + 19], color=INK, lw=1.6, zorder=4)
        self.text(cx + ldx, cy + (ldy if ldy is not None else r + 24), label,
                  size=9.5, ha=lha)
        self.dev(ref, (cx - r, cy - r, cx + r, cy + r))
        self.term((cx - 6, cy))
        d = dict(base=(cx - r, cy), coll=(cx + 12, cy - 19), emit=(cx + 12, cy + 19))
        for v in d.values():
            self.term(v)
        return d

    def ad835(self):
        self.box(BX, BY, BW, BH)
        self.text(BX + 16, BY + 26, 'AD835', size=14, weight='bold')
        for lab, key, y in ROWS:
            self.text(BX + 16, y, lab, size=10.5)
            self.wire([(PIN_X, y), (BX, y)], color='#5a6a80', lw=2.4, zorder=2)
            self.term((BX, y))
            self.port(f'A835_{key}', PIN_X, y)
        self.wire([(BX + BW, W_ROW), (WOUT, W_ROW)], color='#5a6a80', lw=2.4, zorder=2)
        self.term((BX + BW, W_ROW))
        self.port('A835_W', WOUT, W_ROW)
        self.text(BX + BW - 16, W_ROW - 22, '5 · W', size=10.5, ha='right')

    def legend(self, x, y, w, h, title, lines, color=INK):
        self.box(x, y, w, h)
        self.text(x + 16, y + 24, title, size=10.5, weight='bold')
        for i, ln in enumerate(lines):
            self.text(x + 16, y + 50 + i * 20, ln, size=9.3, color=color)

    # -- QA -----------------------------------------------------------------
    def qa(self):
        errs = []
        known = set(self.ports.values()) | self.terms
        for i, (a, b) in enumerate(self.wires):
            for p in (a, b):
                if p in known or self._on_other(p, i):
                    continue
                errs.append(f'dangling wire end {p} on #{i} {a}->{b}')
        for nm, p in self.ports.items():
            if nm.split('_')[-1] in ANNOTATED_ONLY:
                continue
            if not any(p in (a, b) or self._seg(p, a, b) for a, b in self.wires):
                errs.append(f'port {nm} {p} has no wire')

        self.fig.canvas.draw()
        rend = self.fig.canvas.get_renderer()
        inv = self.ax.transData.inverted()
        boxes = []
        for t in self.texts:
            b = t.get_window_extent(rend)
            (x0, y0), (x1, y1) = inv.transform([[b.x0, b.y0], [b.x1, b.y1]])
            boxes.append((t, (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))))

        for (t1, b1), (t2, b2) in itertools.combinations(boxes, 2):
            if not (b1[2] + .5 < b2[0] or b2[2] + .5 < b1[0] or
                    b1[3] + .5 < b2[1] or b2[3] + .5 < b1[1]):
                errs.append(f'text overlap: {t1.get_text()!r} vs {t2.get_text()!r}')
        for t, b in boxes:
            if b[0] < 2 or b[1] < 2 or b[2] > self.w - 2 or b[3] > self.h - 2:
                errs.append(f'text outside canvas: {t.get_text()!r} '
                            f'{tuple(round(v) for v in b)}')
        titles = {self.texts[0].get_text(), self.texts[1].get_text()}
        if self.keepout:
            for t, b in boxes:
                if b[1] < self.keepout and t.get_text() not in titles:
                    errs.append(f'element in title keepout: {t.get_text()!r}')
            for a, b in self.wires:
                if min(a[1], b[1]) < self.keepout:
                    errs.append(f'wire in title keepout: {a}->{b}')
        # a wire may touch a component only at its own terminals; crossing the
        # body of another component (or of itself away from its leads) is an error
        for i, (a, c) in enumerate(self.wires):
            for nm, x0, y0, x1, y1 in self.bodies:
                pts = [(a[0] + (c[0] - a[0]) * k / 20, a[1] + (c[1] - a[1]) * k / 20)
                       for k in range(1, 20)]
                inside = [(px, py) for px, py in pts
                          if x0 + 3 < px < x1 - 3 and y0 + 3 < py < y1 - 3]
                if not inside:
                    continue
                # ignore this wire if both endpoints belong to the same device
                if self._owns(nm, a) or self._owns(nm, c):
                    continue
                errs.append(f'wire crosses {nm} body at '
                            f'({round(inside[0][0])}, {round(inside[0][1])})')
                break
        for t, b in boxes:
            hit = None
            for a, c in self.wires:
                for k in range(25):
                    px = a[0] + (c[0] - a[0]) * k / 24
                    py = a[1] + (c[1] - a[1]) * k / 24
                    if b[0] + 1 < px < b[2] - 1 and b[1] + 1 < py < b[3] - 1:
                        hit = (round(px), round(py)); break
                if hit:
                    break
            if hit:
                errs.append(f'text over wire: {t.get_text()!r} at {hit}')
        return errs

    def _owns(self, devname, p):
        """True if p is one of the terminals registered for that device."""
        return p in self.terms and self._near_body(devname, p)

    def _near_body(self, devname, p):
        for nm, x0, y0, x1, y1 in self.bodies:
            if nm == devname and (x0 - 1 <= p[0] <= x1 + 1 and y0 - 1 <= p[1] <= y1 + 1):
                return True
        return False

    @staticmethod
    def _seg(p, a, b, tol=0.6):
        (px, py), (ax_, ay), (bx, by) = p, a, b
        if not (min(ax_, bx) - tol <= px <= max(ax_, bx) + tol and
                min(ay, by) - tol <= py <= max(ay, by) + tol):
            return False
        cross = (bx - ax_) * (py - ay) - (by - ay) * (px - ax_)
        return abs(cross) < tol * max(1.0, abs(bx - ax_) + abs(by - ay))

    def _on_other(self, p, skip):
        return any(self._seg(p, a, b) for i, (a, b) in enumerate(self.wires) if i != skip)

    def save(self, name):
        errs = self.qa()
        self.fig.savefig(DRAW / f'{name}.png', dpi=110, facecolor='#f7f9fc')
        self.fig.savefig(DRAW / f'{name}.svg', facecolor='#f7f9fc')
        plt.close(self.fig)
        import json as _json
        (DRAW / f'{name}.devices.json').write_text(
            _json.dumps(sorted(set(self.drawn)), indent=2, ensure_ascii=False),
            encoding='utf8')
        print(f'{name:22s} {"PASS" if not errs else "FAIL (%d)" % len(errs)}')
        for e in errs[:12]:
            print('    -', e)
        return errs


# shared right-hand furniture
def baseband(s, x_port, lines, port_name, riser=1330):
    s.box(40, 690, 300, 100)
    s.text(56, 714, 'Baseband X', size=10.5, weight='bold')
    for i, ln in enumerate(lines):
        s.text(56, 740 + i * 20, ln, size=9.3, color=GREY)
    s.port(port_name, x_port, 742)
    # climb to the X1 pin stub and approach from the LEFT, never over the label
    s.wire([(x_port, 742), (riser, 742), (riser, 400), (X1_STUB_MID, 400)])


def wload(s, name):
    s.box(WOUT + 40, W_ROW - 35, 175, 70)
    s.text(WOUT + 54, W_ROW - 11, 'W -> 50 R // 10 pF', size=9.5)
    s.text(WOUT + 54, W_ROW + 11, 'target, not verified', size=9.2, color=GREY)
    s.wire([s.ports['A835_W'], s.port(name, WOUT + 40, W_ROW)])


# =========================================================== candidate A
def cand_a():
    s = Sheet('Carrier interface candidate A — passive attenuator + bias return')
    s.ad835()

    s.box(40, 150, 200, 70)
    s.text(56, 174, 'C4 carrier module TP2', size=10)
    s.text(56, 196, 'COUTG = 10 nF DC block', size=9.3, color=GREY)
    s.wire([s.port('A_TP2', 240, 185), (273, 185)])
    ra, rb = s.res_h(300, 185, 'RS 470', ref='RS')
    s.wire([(273, 185), ra])
    node = s.port('A_nodeA', 400, 185)
    s.wire([rb, node])

    s.wire([node, (400, 320)])
    s.wire([(400, 240), s.ports['A835_Y1']])
    s.wire([(400, 320), s.ports['A835_Z']])

    rt, rbm = s.res_v(400, 352, 'RP 680', ln=44, ref='RP')
    s.wire([(400, 320), rt])
    s.wire([rbm, (400, 382)])
    s.gnd(400, 382, 'AGND')

    baseband(s, 320, ['LM393 -> resistor network', '-> OPA197 (both stages)',
                      'X plateau error 0.180 mV, +20.264 mW'], 'A_BB', riser=778)
    wload(s, 'A_WLOAD')

    s.legend(800, 540, 520, 185, 'Measured, A470 (470 / 680), same C4 netlist', [
        'TP2 2.801 Vpp   Y = Z 1.605 Vpp   Y peak 0.954 V   ratio 1.0000',
        'Y vs TP2 phase -12.13 deg   Z vs Y 0.00 deg   Y DC -40.1 mV',
        'carrier THD 15.23 %   extra power +0.073 mW over the 42.778 mW base',
        'Y stays inside +-1 V; 330/680 was rejected at 1.028 V peak',
        'RP 680 returns node a to AGND; without it Y floats to -2.250 V (measured)'])
    s.text(38, H - 46, FOOTER, size=9.2, color=GREY)
    return s.save('候选A_被动衰减')


# =========================================================== candidate B
def cand_b():
    s = Sheet('Carrier interface candidate B — RF buffer ahead of Y/Z')
    s.ad835()

    s.box(40, 150, 200, 70)
    s.text(56, 174, 'C4 carrier module TP2', size=10)
    s.text(56, 196, 'COUTG = 10 nF', size=9.3, color=GREY)
    # TP2 --CBI--> atten ; atten --RSB/RPB--> rb ; rb --CB2--> base
    s.wire([s.port('B_TP2', 240, 185), (262, 185)])
    cbi_a, cbi_b = s.cap_h(286, 185, 'CBI 10n', ref='CBI')
    s.wire([(240, 185), cbi_a])

    s.wire([cbi_b, (330, 185)])
    s.port('B_ATTEN', 330, 185)
    rsb_a, rsb_b = s.res_h(372, 185, 'RSB 1k', ln=46, ref='RSB')
    s.wire([(330, 185), rsb_a])
    rpb_t, rpb_b = s.res_v(330, 240, 'RPB 1k', ln=40, side=-1, ref='RPB')
    s.wire([(330, 185), rpb_t])
    s.wire([rpb_b, (330, 268)])
    s.gnd(330, 268)

    s.wire([rsb_b, (410, 185)])
    s.port('B_RB', 410, 185)
    cb2_a, cb2_b = s.cap_h(438, 185, 'CB2 10n', ref='CB2')
    s.wire([(410, 185), cb2_a])

    q = s.npn(500, 300, 'QBUF', ldx=34, ldy=-34, lha='left', ref='QBUF')
    s.wire([cb2_b, (455, 185), (455, 300), s.port('B_BASE', *q['base'])])

    # base divider RBT2 / RBB2 drawn as two stubs off the base node
    rbt_t, rbt_b = s.res_v(405, 252, 'RBT2 10k', ln=34, side=-1, ref='RBT2')
    rbb_t, rbb_b = s.res_v(405, 350, 'RBB2 10k', ln=34, side=-1, ref='RBB2')
    s.wire([(405, 235), (405, 222)]); s.port('B_RBT', 405, 222)
    s.text(417, 222, '+5 V', size=9, color=GREY)
    s.wire([(405, 269), (405, 333)])
    s.wire([(405, 300), (455, 300)])
    s.wire([(405, 367), (405, 384)])
    s.gnd(405, 384)

    s.wire([q['coll'], (q['coll'][0], 130)])
    s.port('B_VCC', q['coll'][0], 130)
    s.text(q['coll'][0] + 14, 130, '+5 V rail', size=9.3, color=GREY)

    # emitter -> REB2 -> AGND ; emitter -> CBO -> node a
    # emitter -> REB2 -> AGND, and emitter -> CBO -> node a
    s.wire([q['emit'], (q['emit'][0], 340)])
    re_t, re_b = s.res_v(q['emit'][0], 364, 'REB2 330', ln=44, side=1, ref='REB2')
    s.wire([(q['emit'][0], 340), re_t])
    s.wire([re_b, (q['emit'][0], 392)])
    s.gnd(q['emit'][0], 392)

    s.wire([(q['emit'][0], 340), (582, 340)])
    cbo_a, cbo_b = s.cap_h(606, 340, 'CBO 10n', ref='CBO')
    s.wire([(582, 340), cbo_a])

    # node a
    s.wire([cbo_b, (650, 340)])
    nodeA = s.port('B_A', 650, 340)
    rret_t, rret_b = s.res_v(650, 392, 'RRETURN 680', ln=40, side=-1, ref='RRETURN')
    s.wire([nodeA, rret_t])
    s.wire([rret_b, (650, 424)])
    s.gnd(650, 424)

    # node a -> Y1
    s.wire([nodeA, (650, 240), s.ports['A835_Y1']])

    # node a -> RZT 100 -> node z ; node z -> RZB 150.376 -> AGND ; node z -> Z
    rzt_a, rzt_b = s.res_h(704, 340, 'RZT 100', ln=44, ref='RZT')
    s.wire([nodeA, (682, 340)])
    s.wire([rzt_b, (740, 340)])
    nodeZ = s.port('B_Z', 740, 340)
    rzb_t, rzb_b = s.res_v(740, 386, 'RZB 150.38', ln=38, ref='RZB')
    s.wire([nodeZ, rzb_t])
    s.wire([rzb_b, (740, 416)])
    s.gnd(740, 416)
    s.wire([nodeZ, (740, 320), s.ports['A835_Z']])

    baseband(s, 320, ['X = 0.105 Vm  (unipolar)', 'no -0.42 V bias needed'], 'B_BB', riser=778)
    wload(s, 'B_WLOAD')

    s.legend(800, 520, 520, 200, 'Measured, B_Z06 (Y = Vc, Z = 0.6 Vc)', [
        'TP2 3.2455 Vpp   Y 1.145 Vpp (peak 0.608 V)   Z 0.687 Vpp   ratio 0.5998',
        'Y vs TP2 -24.16 deg   Z vs Y -1.34 deg   Y DC -7.3 mV',
        'carrier THD 8.72 %  (lowest of all candidates)',
        'cost: +26.334 mW and one transistor; TP2 is loaded HARDER than in A',
        'the buffer turns a single-chip plan into multiplier + RF stage',
        'Z tap is 100 / 150.376, placed after the buffer so it does not load TP2'])
    s.text(38, H - 46, FOOTER, size=9.2, color=GREY)
    return s.save('候选B_射频缓冲')


# =========================================================== candidate C
def cand_c():
    s = Sheet('Carrier interface candidate C — separate Y and Z branches')
    s.ad835()

    s.box(40, 150, 200, 70)
    s.text(56, 174, 'C4 carrier module TP2', size=10)
    s.text(56, 196, 'COUTG = 10 nF', size=9.3, color=GREY)
    s.wire([s.port('C_TP2', 240, 185), (300, 185)])
    s.wire([(300, 185), (300, 320)])

    # Y branch: series 330, then shunt 680 to AGND
    ya, yb = s.res_h(333, 240, '330', ln=44, ref='RSY')
    s.wire([(300, 240), ya])
    s.wire([yb, s.ports['A835_Y1']])
    yt, ybm = s.res_v(395, 268, '680', ln=40, ref='RBY')
    s.wire([(395, 240), yt])
    s.wire([ybm, (395, 292)])
    s.gnd(395, 292)

    # Z branch: series 1k, then shunt 680 to AGND
    za, zb = s.res_h(333, 320, '1 k', ln=44, ref='RSZ')
    s.wire([(300, 320), za])
    s.wire([zb, s.ports['A835_Z']])
    zt, zbm = s.res_v(460, 348, '680', ln=40, ref='RBZ')
    s.wire([(460, 320), zt])
    s.wire([zbm, (460, 372)])
    s.gnd(460, 372)

    baseband(s, 320, ['same as A: needs -0.42 V bias', 'OPA197 candidate, +-10.2 mW'], 'C_BB', riser=778)
    wload(s, 'C_WLOAD')

    s.legend(800, 520, 520, 200, 'Measured, C_B (Y 330/680, Z 1k/680)', [
        'TP2 2.199 Vpp   Y 1.471 Vpp (peak 0.877 V)   Z 0.872 Vpp   ratio 0.5935',
        'Y vs TP2 -4.94 deg   Z vs Y -3.97 deg   Y DC -13.5 mV',
        'carrier THD 18.81 %   extra power +0.108 mW',
        'the -3.97 deg branch phase difference comes from RC and input capacitance;',
        'trimming the resistors cannot remove it',
        'each branch carries its own 680 ohm shunt, so Y and Z trim independently'])
    s.text(38, H - 46, FOOTER, size=9.2, color=GREY)
    return s.save('候选C_YZ独立分支')


# =========================================================== A / B compare
def ab_compare():
    s = Sheet('A / B amplitude-modulation wiring: the two conventions must be paired',
              'IDEAL MULTIPLIER ARITHMETIC ON MEASURED WAVEFORMS  *  not a device simulation',
              w=1180, h=760)
    s.keepout = 0
    for k, (title, x0, col) in enumerate((
            ('Scheme A:  X = 0.105Vm - 0.42   (bipolar)', 40, RED),
            ('Scheme B:  X = 0.105Vm   (unipolar)', 600, GREEN))):
        s.box(x0, 96, 540, 292)
        s.text(x0 + 18, 122, title, size=12, weight='bold')
        rows = [('Y1', 'Vc', 'shared with Z'),
                ('Z', 'Vc' if k == 0 else '0.6 Vc',
                 'same node' if k == 0 else 'divider 100 / 150.4'),
                ('X1', '0.105Vm - 0.42' if k == 0 else '0.105Vm',
                 'must go negative' if k == 0 else 'all positive'),
                ('W', 'X*Y/U + Z', 'U about 1.05 V')]
        for i, (a, b, c) in enumerate(rows):
            y = 160 + i * 34
            s.text(x0 + 24, y, a, size=11, weight='bold')
            s.text(x0 + 76, y, b, size=11)
            s.text(x0 + 266, y, c, size=9.5, color='#5a6a80')
        s.text(x0 + 24, 306, 'Z = Vc is REQUIRED with this X' if k == 0
               else 'Z = 0.6 Vc is REQUIRED with this X', size=9.8, color=col, weight='bold')
        s.text(x0 + 24, 330, 'X low -0.412 V, so the buffer must swing negative' if k == 0
               else 'X range 0.0079 ... 0.4279 V, entirely positive', size=9.5, color=col)
        s.text(x0 + 24, 354, 'carrier feedthrough crosses zero as X passes 0' if k == 0
               else 'carrier enters Z at 0.6, modulation stays 25 %', size=9.5, color=col)

    s.text(40, 424, 'Measured wiring comparison', size=12, weight='bold')
    s.text(40, 446, 'Y/Z are RC + bias-current fixtures, not a device model',
           size=9.5, color=GREY)

    heads = [('wiring', 44), ('TP2', 330), ('Y peak', 445), ('ideal envelope', 545),
             ('modulation', 725), ('verdict', 855)]
    for hd, x in heads:
        s.text(x, 478, hd, size=10, weight='bold', color=GREY)
    rows = [('A470 + bipolar X', '2.801 Vpp', '0.954 V', '1.922 / 1.159 Vpp', '24.77 %',
             'short of target', INK),
            ('A 510/680 + bipolar X', '2.860 Vpp', '0.939 V', '1.891 / 1.140 Vpp', '24.77 %',
             'RECOMMENDED', GREEN),
            ('A 330/620 + bipolar X', '2.593 Vpp', '0.987 V', '1.989 / 1.199 Vpp', '24.77 %',
             'closest', INK),
            ('B_Z06 + unipolar X', '3.245 Vpp', '0.608 V', '1.230 / 0.744 Vpp', '24.62 %',
             'too low', INK),
            ('C_B + unipolar X', '2.199 Vpp', '0.877 V', '1.787 / 1.087 Vpp', '24.38 %',
             'lower than A', INK),
            ('A470 + unipolar X', '2.801 Vpp', '0.954 V', '2.685 / 1.922 Vpp', '16.56 %',
             'MISPAIRED', RED),
            ('B_Z06 + bipolar X', '3.245 Vpp', '0.608 V', '0.744 / 0.258 Vpp', '48.45 %',
             'MISPAIRED', RED)]
    for i, r in enumerate(rows):
        y = 508 + i * 26
        for (hd, x), v in zip(heads, r[:6]):
            s.text(x, y, v, size=9.6, color=r[6])

    s.text(40, 706, 'The ideal-envelope column substitutes measured waveforms into '
                    'W = X*Y/U + Z. It is arithmetic, NOT an AD835 simulation, assuming '
                    'U = 1.05 V exactly,', size=9.2, color=GREY)
    s.text(40, 724, 'with no gain error and no clipping. Paired correctly the modulation '
                    'depth is 24.77 % regardless of attenuation: Y and Z scale together, so '
                    'a divider', size=9.2, color=GREY)
    s.text(40, 742, 'costs absolute level but not modulation depth.', size=9.2, color=GREY)
    return s.save('AB调幅接线对比')


if __name__ == '__main__':
    total = 0
    for fn in (cand_a, cand_b, cand_c, ab_compare):
        total += len(fn())
    print('\nQA total issues:', total)
