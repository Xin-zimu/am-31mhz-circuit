"""Read-only: (a) do the engine's .options cards do anything at all?
(b) does any saved node cross a switch threshold at the GUI death time?

No simulator calls.
"""
from pathlib import Path
import sys
import hashlib
import json
import xml.etree.ElementTree as ET
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
E = K / 'gui_evidence_20261014'
STG = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

res = {}

# ---------------------------------------------------------------------------
print('=' * 88)
print('A. ARE THE ENGINE .options CARDS ACTUALLY HONOURED?')
print('=' * 88)
groups = {
    'O-series (reltol/trtol/itl4/method/convlimit on same 2us run)':
        sorted((STG / 's0304').glob('O*.raw')),
    'U-series (26 solver knobs, same short run)':
        sorted((STG / 's0304').glob('U*.raw')),
    'L-series (reltol 1e-2 vs 1e-9 via option vs set)':
        sorted((STG / 's0304').glob('L[0-9]*.raw')),
    'X-series (options before/after source)':
        sorted((STG / 's0304').glob('X*.raw')),
    'Y-series (options card placement)':
        sorted((STG / 's0304').glob('Y*.raw')),
}
for label, files in groups.items():
    if not files:
        continue
    digests = {}
    shapes = {}
    for f in files:
        if f.stat().st_size < 2000:
            shapes[f.stem] = f'only {f.stat().st_size} B (degenerate run)'
            continue
        try:
            _, v = read_raw(f)
        except Exception as exc:                       # noqa: BLE001
            shapes[f.stem] = f'unreadable ({exc})'
            continue
        digests.setdefault(hashlib.sha256(v.tobytes()).hexdigest(), []).append(f.stem)
        shapes[f.stem] = v.shape
    print(f'\n  {label}   ({len(files)} runs)')
    for name, shape in shapes.items():
        print(f'    {name:34s} {shape}')
    if digests:
        print(f'    -> distinct numeric results: {len(digests)}')
        for h, names in digests.items():
            print(f'       {h[:16]}... : {", ".join(names)}')
    res[label] = {'distinct_results': len(digests),
                  'groups': {h[:16]: n for h, n in digests.items()}}

# ---------------------------------------------------------------------------
print()
print('=' * 88)
print('B. SWITCH THRESHOLDS PRESENT IN THIS NETLIST')
print('=' * 88)
net = (S / 'cold_engine_gui_net.cir').read_text(encoding='utf-8-sig', errors='replace')
import re
for m in sorted(set(re.findall(r'\.MODEL\s+(\S+)\s+VSWITCH\s*\(?([^)\n]*)', net, re.I))):
    print(f'  {m[0]:10s} {m[1].strip()}')
print()
print('  Node voltage ranges actually saved by these runs (engine 20 us run):')
names, v = read_raw(STG / 'cold_engine_gui_net.raw')
labels = ['V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)']
ranges = {}
for i, lab in enumerate(labels, start=1):
    col = v[:, i]
    rng = (float(col.min()), float(col.max()))
    ranges[lab] = rng
    print(f'    {lab:10s} min={rng[0]:+.6f} V   max={rng[1]:+.6f} V')
res['node_ranges_20us'] = ranges

# ---------------------------------------------------------------------------
print()
print('=' * 88)
print('C. THRESHOLD CROSSINGS NEAR THE GUI DEATH TIME (225.80 ns)')
print('=' * 88)
et = v[:, 0]
g = {}
root = ET.parse(E / 'S03_GUI_COLD_20us_gra.xml').getroot()
for tr in root.iter('CTrace'):
    d = tr.find('Data')
    if d is None:
        continue
    nm = tr.get('Name').removeprefix('&ASC')
    g[nm] = (np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8'),
             np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8'))
gt = g['V(v1)'][0]
stop = float(gt[-1])

THRESH = [0.0, 0.010, 0.100, 0.700, 0.800, 0.900, 4.5]
print(f'  GUI run stops at {stop*1e9:.6f} ns')
for lab in labels:
    eng_col = v[:, labels.index(lab) + 1]
    gui_col = g[lab][1]
    print(f'\n  {lab}')
    for th in THRESH:
        # engine: first crossing of th after 100 ns
        sgn_e = np.sign(eng_col - th)
        xe = np.flatnonzero((sgn_e[:-1] != sgn_e[1:]) & (et[:-1] > 100e-9))
        sgn_g = np.sign(gui_col - th)
        xg = np.flatnonzero(sgn_g[:-1] != sgn_g[1:])
        te = f'{et[xe[0]]*1e9:10.4f} ns' if len(xe) else '     --    '
        tg = f'{gt[xg[0]]*1e9:10.4f} ns' if len(xg) else '     --    '
        near = ''
        if len(xg) and abs(gt[xg[0]] - stop) < 2e-9:
            near = '   <== AT the GUI death time'
        print(f'    crosses {th:+.3f} V : engine first {te} | GUI first {tg}{near}')

# ---------------------------------------------------------------------------
print()
print('=' * 88)
print('D. GUI STEP-SIZE PROFILE (is the solver struggling from the start?)')
print('=' * 88)
gdt = np.diff(gt)
bins = [(0, 0.05), (0.05, 0.2), (0.2, 0.5), (0.5, 0.9), (0.9, 1.01)]
print(f'  {"dt range (ns)":>16s} {"count":>7s} {"share":>8s}')
for lo, hi in bins:
    n = int(((gdt >= lo * 1e-9) & (gdt < hi * 1e-9)).sum())
    print(f'  {f"{lo}-{hi}":>16s} {n:7d} {100*n/len(gdt):7.2f}%')
print()
print('  same bins for the engine (identical netlist, 20 us):')
edt = np.diff(et)
print(f'  {"dt range (ns)":>16s} {"count":>7s} {"share":>8s}')
for lo, hi in bins:
    n = int(((edt >= lo * 1e-9) & (edt < hi * 1e-9)).sum())
    print(f'  {f"{lo}-{hi}":>16s} {n:7d} {100*n/len(edt):7.2f}%')
res['gui_dt_share'] = {f'{lo}-{hi}': float(((gdt >= lo*1e-9) & (gdt < hi*1e-9)).mean())
                       for lo, hi in bins}
res['engine_dt_share'] = {f'{lo}-{hi}': float(((edt >= lo*1e-9) & (edt < hi*1e-9)).mean())
                          for lo, hi in bins}

# ---------------------------------------------------------------------------
print()
print('=' * 88)
print('E. THE ARITHMETIC OF THE STOP TIME')
print('=' * 88)
CAP = 1.0080645161290323e-9
print(f'  effective cap seen in every run        = {CAP*1e9:.10f} ns')
print(f'  carrier period / 32                    = {1/31e6/32*1e9:.10f} ns')
print(f'  224 x cap                              = {224*CAP*1e9:.6f} ns')
print(f'  7 x carrier period                     = {7/31e6*1e9:.6f} ns')
print(f'  GUI stop                               = {stop*1e9:.6f} ns')
print(f'  GUI stop / cap                         = {stop/CAP:.4f} steps-at-cap')
print(f'  GUI stop / carrier period              = {stop*31e6:.6f} cycles')
res['stop_over_cap'] = float(stop / CAP)
res['stop_over_period'] = float(stop * 31e6)

(OUT / 'mechanism_analysis.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
