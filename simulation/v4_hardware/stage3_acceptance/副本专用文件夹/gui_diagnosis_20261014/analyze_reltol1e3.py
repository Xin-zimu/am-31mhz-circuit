"""Read-only analysis of the RELTOL=1e-3 native-GUI run against the archive.

Compares the new GUI run with:
  - the earlier FAILED GUI run (RELTOL=1e-4), same project
  - the command engine on the same netlist
No simulator calls.
"""
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
E = K / 'gui_evidence_20261014'
STG = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

F0 = 31e6
PERIOD = 1 / F0
NEW = E / 'S03_GUI_COLD_20us_reltol1e3.xml'
OLD = E / 'S03_GUI_COLD_20us_gra.xml'
res = {}


def traces(path):
    root = ET.parse(path).getroot()
    pages = list(root.iter('CGraphPage'))
    out, metas = {}, []
    for tr in root.iter('CTrace'):
        d = tr.find('Data')
        if d is None:
            continue
        nm = tr.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(d.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(d.get('YData')), dtype='<f8')
        out[nm] = (x, y)
    for pg in pages:
        labels = [{k: v for k, v in el.attrib.items()
                   if k in ('Text', 'Name', 'Title', 'Label')}
                  for el in pg.iter() if any('S03' in str(v) for v in el.attrib.values())]
        metas.append({'attributes': dict(pg.attrib), 'labels': labels})
    return out, metas, len(pages)


print('=' * 96)
print('1. THE NEW NATIVE-GUI RUN  (RELTOL=1e-3, TRTOL=7)')
print('=' * 96)
new, new_meta, new_pages = traces(NEW)
print(f'  file      : {NEW.name}  ({NEW.stat().st_size/1e6:.2f} MB decoded XML)')
print(f'  pages     : {new_pages}')
for m in new_meta:
    for lb in m['labels'][:3]:
        print(f'  page label: {lb}')
print()
order = ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']
print(f'  {"trace":>10s} {"points":>9s} {"start (ns)":>13s} {"end (us)":>12s} '
      f'{"dt min (ps)":>12s} {"dt max (ps)":>12s}')
for nm in order:
    if nm not in new:
        print(f'  {nm:>10s}   MISSING')
        continue
    x, y = new[nm]
    dt = np.diff(x)
    print(f'  {nm:>10s} {len(x):9d} {x[0]*1e9:13.6f} {x[-1]*1e6:12.6f} '
          f'{dt.min()*1e12:12.4f} {dt.max()*1e12:12.4f}')

xt = new['V(v1)'][0]
print()
print(f'  REACHED 20 us : {abs(xt[-1] - 20e-6) < 1e-9}')
print(f'  end / periods : {xt[-1]/PERIOD:.4f}')
print(f'  monotonic t   : {bool((np.diff(xt) > 0).all())}')
print(f'  all finite    : {bool(np.isfinite(xt).all() and all(np.isfinite(new[n][1]).all() for n in new))}')
res['new'] = {'pages': new_pages, 'end_s': float(xt[-1]), 'points': int(len(xt)),
              'dt_max_s': float(np.diff(xt).max()), 'dt_min_s': float(np.diff(xt).min())}

print()
print('=' * 96)
print('2. OLD FAILED RUN vs NEW RUN  (same project, only RELTOL/TRTOL changed)')
print('=' * 96)
old, _, old_pages = traces(OLD)
ot = old['V(v1)'][0]
print(f'  {"":28s} {"OLD (reltol 1e-4)":>22s} {"NEW (reltol 1e-3)":>22s}')
for label, a, b in [('config', 'TSTEP=TMAX=1 ns, UIC', 'TSTEP=TMAX=1 ns (same project)'),
                    ('points', f'{len(ot)}', f'{len(xt)}'),
                    ('end', f'{ot[-1]*1e9:.6f} ns', f'{xt[-1]*1e6:.6f} us'),
                    ('end / carrier periods', f'{ot[-1]/PERIOD:.4f}', f'{xt[-1]/PERIOD:.4f}'),
                    ('step median (ps)', f'{np.median(np.diff(ot))*1e12:.3f}',
                     f'{np.median(np.diff(xt))*1e12:.3f}'),
                    ('step max (ps)', f'{np.diff(ot).max()*1e12:.3f}',
                     f'{np.diff(xt).max()*1e12:.3f}'),
                    ('deepest step (ps)', f'{np.diff(ot).min()*1e12:.4f}',
                     f'{np.diff(xt).min()*1e12:.4f}'),
                    ('outcome', 'ABORTED at 225.8 ns', 'COMPLETED 20 us'
                     if abs(xt[-1]-20e-6) < 1e-9 else 'still short')]:
    print(f'  {label:28s} {a:>22s} {b:>22s}')

print()
print('=' * 96)
print('3. LOOK FOR THE 225.806 ns EVENT IN THE NEW RUN')
print('=' * 96)
EVENT = 7 * PERIOD
m = np.abs(xt - EVENT) < 3e-9
print(f'  event time = {EVENT*1e9:.6f} ns')
if m.any():
    idx = np.flatnonzero(m)
    dt = np.diff(xt)
    seg = dt[np.clip(idx - 1, 0, len(dt) - 1)]
    print(f'  samples within +/-3 ns : {len(idx)}')
    print(f'  smallest step there    : {seg.min()*1e12:.4f} ps')
    print(f'  (old run had to descend to 0.0116 ps here, then aborted)')
else:
    print('  no sample within +/-3 ns (step is coarse there)')

print()
print(f'  {"window (ns)":>18s} {"#samples":>9s} {"min dt (ps)":>12s} {"max dt (ps)":>12s}')
dt = np.diff(xt)
for lo, hi in [(0, 32.26), (193.55, 225.81), (225.81, 258.06), (258.06, 322.58),
               (1000, 1100), (5000, 5100), (19990, 20000)]:
    w = (xt[1:] >= lo * 1e-9) & (xt[1:] < hi * 1e-9)
    if not w.any():
        continue
    print(f'  {f"{lo}-{hi}":>18s} {int(w.sum()):9d} {dt[w].min()*1e12:12.4f} '
          f'{dt[w].max()*1e12:12.4f}')

print()
print('=' * 96)
print('4. AGAINST THE COMMAND ENGINE (same netlist, cold start)')
print('=' * 96)
names, v = read_raw(STG / 'cold_engine_gui_net.raw')
et = v[:, 0]
# column order in .raw: 0=time, 1=V(bb_in), 2=V(bbo), 3=V(v1), 4=V(v2)
IB, IV2 = 1, 4
print(f'  engine run: {len(et)} points to {et[-1]*1e6:.3f} us')
print(f'  columns   : {names}')
print()
print(f'  {"t (us)":>10s} {"GUI bb_in":>12s} {"ENG bb_in":>12s} {"diff (mV)":>11s} '
      f'{"GUI v2":>11s} {"ENG v2":>11s} {"diff (mV)":>11s}')
for tk in [0.5e-6, 1e-6, 2e-6, 5e-6, 10e-6, 15e-6, 19.5e-6, 19.999e-6]:
    jg = int(np.searchsorted(xt, tk))
    je = int(np.searchsorted(et, tk))
    if jg >= len(xt) or je >= len(et):
        continue
    d1 = (new['V(bb_in)'][1][jg] - v[je, IB]) * 1e3
    d2 = (new['V(v2)'][1][jg] - v[je, IV2]) * 1e3
    print(f'  {xt[jg]*1e6:10.4f} {new["V(bb_in)"][1][jg]:12.6f} {v[je, IB]:12.6f} {d1:11.3f} '
          f'{new["V(v2)"][1][jg]:11.6f} {v[je, IV2]:11.6f} {d2:11.3f}')

# ---- the decisive step-control comparison
print()
print('=' * 96)
print('5. STEP CONTROL: THE MECHANISM CONFIRMED')
print('=' * 96)
gdt = np.diff(xt)
edt = np.diff(et)
m = et <= xt[-1]
edt_cmp = np.diff(et[m])
print(f'  {"":34s} {"GUI 1e-4 (FAIL)":>17s} {"GUI 1e-3 (PASS)":>17s} {"ENGINE":>12s}')
odt = np.diff(ot)
for label, fn in [('median step (ps)', lambda d: np.median(d) * 1e12),
                  ('mean step (ps)', lambda d: d.mean() * 1e12),
                  ('% at the 1 ns ceiling', lambda d: 100 * (d > 0.999e-9).mean()),
                  ('deepest step at 225.8 ns (ps)',
                   lambda d: d[np.abs(np.arange(len(d)) - len(d)) >= 0][:1].sum() if False else np.nan)]:
    if label.startswith('deepest'):
        continue
    print(f'  {label:34s} {fn(odt):17.3f} {fn(gdt):17.3f} {fn(edt_cmp):12.3f}')
# deepest at the event, computed per run
for label, t_, d_ in [('GUI 1e-4 (FAIL)', ot, odt), ('GUI 1e-3 (PASS)', xt, gdt),
                      ('ENGINE', et, edt)]:
    w = np.abs(t_[1:] - 7 / 31e6) < 3e-9
    if w.any():
        print(f'  {"deepest step at event (" + label + ")":34s} {d_[w].min()*1e12:17.4f} ps')

(OUT / 'gui_reltol1e3_analysis.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "gui_reltol1e3_analysis.json"}')
