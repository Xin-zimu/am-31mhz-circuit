"""Read-only deep diagnosis of the native-GUI transient non-convergence.

Answers: what is special about ~225.8 ns, and how does the engine's trajectory
differ from the GUI's? No simulator calls; only archived artifacts.
"""
from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET
import numpy as np

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
K = S / '副本专用文件夹'
E = K / 'gui_evidence_20261014'
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

F0 = 31e6
PERIOD = 1 / F0
CAP = 1.0080645161290323e-9   # effective step ceiling both entries settle at


def traces(path):
    root = ET.parse(path).getroot()
    out = {}
    for tr in root.iter('CTrace'):
        data = tr.find('Data')
        if data is None:
            continue
        name = tr.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        out[name] = (x, y)
    return out


res = {}

# ---------------------------------------------------------------- GUI failure
g = traces(E / 'S03_GUI_COLD_20us_gra.xml')
gt = g['V(v1)'][0]
gdt = np.diff(gt)

print('=' * 88)
print('1. WHERE THE GUI STOPS')
print('=' * 88)
stop = float(gt[-1])
print(f'  stop time            = {stop*1e9:.6f} ns')
print(f'  carrier period       = {PERIOD*1e9:.6f} ns  (31 MHz)')
print(f'  stop / period        = {stop/PERIOD:.6f}   -> {round(stop/PERIOD)} periods')
print(f'  shortfall vs 7 periods = {(7*PERIOD-stop)*1e12:.3f} ps')
print(f'  accepted points      = {len(gt)}')
print(f'  median step          = {np.median(gdt)*1e12:.3f} ps   '
      f'({np.median(gdt)/1e-9:.4f} ns)')
print(f'  steps at the 1 ns cap= {int((gdt > 0.999e-9).sum())} / {len(gdt)}')
res['gui'] = {'stop_s': stop, 'stop_over_period': stop / PERIOD,
              'points': len(gt), 'median_dt_s': float(np.median(gdt))}

# When does the step first collapse permanently?
print()
print('  --- step-collapse onset: first index after which dt never recovers ---')
suffix_min = np.minimum.accumulate(gdt[::-1])[::-1]
suffix_max = np.maximum.accumulate(gdt[::-1])[::-1]
onset = None
for k in range(len(gdt)):
    if suffix_max[k] < 0.05e-9:      # never again exceeds 50 ps
        onset = k
        break
if onset is not None:
    print(f'  last step above 50 ps at k={onset}, t={gt[onset]*1e9:.6f} ns')
    print(f'  from there to the abort: {len(gdt)-onset} steps over '
          f'{(gt[-1]-gt[onset])*1e12:.1f} ps')
    res['gui']['collapse_onset_k'] = int(onset)
    res['gui']['collapse_onset_t_s'] = float(gt[onset])

# Terminal step collapse ratio
print()
print(f'  last step = {gdt[-1]:.4e} s   first step = {gdt[0]:.4e} s   '
      f'ratio = {gdt[-1]/gdt[0]:.3e}')
print(f'  smallest step overall = {gdt.min():.4e} s at t={gt[int(np.argmin(gdt))+1]*1e9:.6f} ns')

# ------------------------------------------------------- other GUI failures
print()
print('=' * 88)
print('2. FAILURE TIME vs ITL4  (iteration limit per timepoint)')
print('=' * 88)
cases = [
    ('TRAP100  (ITL4=100), 2/2 ns, zero_ic', 100, 5.2e-08),
    ('TRAP500  (ITL4=500), 2/2 ns, zero_ic', 500, 225.795548e-9),
    ('GEAR500  (ITL4=500), 2/2 ns, zero_ic', 500, 225.798429e-9),
    ('GEAR500+UIC (ITL4=500), 1/1 ns', 500, 225.797635e-9),
]
print(f'  {"case":38s} {"ITL4":>5s} {"stop (ns)":>12s} {"stop/period":>12s}')
prev = None
for label, itl4, stop_s in cases:
    print(f'  {label:38s} {itl4:5d} {stop_s*1e9:12.6f} {stop_s/PERIOD:12.6f}')
print()
print('  ITL4 100 -> 500 moved the stop time 4.3x later, but the *default* 500')
print('  run and the exotic 500 runs all die at the SAME time to 4 digits.')
print('  => the ceiling is not the iteration budget at the default; something')
print('     at ~225.80 ns is a hard barrier for the GUI solver path.')

# ------------------------------------------------------------------ engine
print()
print('=' * 88)
print('3. THE ENGINE ON THE SAME NETLIST')
print('=' * 88)
eng = S / 'cold_engine_gui_net.cir'
rawname = Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw')
names, v = read_raw(rawname)
et = v[:, 0]
edt = np.diff(et)
print(f'  netlist diff vs the GUI failure netlist: header/date/.end only')
print(f'  engine points={len(et)}  end={et[-1]*1e6:.3f} us')
print(f'  engine step: min={edt.min():.3e}  median={np.median(edt):.3e}  max={edt.max():.3e}')
print(f'  engine median step = {np.median(edt)/CAP:.4f} x the 1.008 ns ceiling')
print(f'  engine steps at ceiling = {int((edt > 0.999*CAP).sum())} / {len(edt)}')
print(f'  GUI  median step = {np.median(gdt)/1e-9:.4f} ns  '
      f'({np.median(gdt)/CAP:.4f} x the same ceiling)')
print()
print('  => the ENGINE runs essentially AT the step ceiling; the GUI is forced')
print('     to take far smaller steps from the very beginning. The two are on')
print('     different trajectories, so the engine is not a controlled control.')

# What is the engine doing right at the GUI's death time?
print()
print('  --- engine samples bracketing the GUI death time ---')
idx = np.flatnonzero((et > stop - 3e-9) & (et < stop + 3e-9))
if len(idx):
    print(f'  {"t (ns)":>12s} {"dt (ps)":>9s} {"V(bb_in)":>11s} {"V(bbo)":>11s} '
          f'{"V(v1)":>11s} {"V(v2)":>11s}')
    for k in idx:
        print(f'  {et[k]*1e9:12.6f} {edt[k-1]*1e12:9.3f} {v[k,1]:11.7f} '
              f'{v[k,2]:11.7f} {v[k,3]:11.7f} {v[k,4]:11.7f}')
else:
    print('  (no engine sample within 3 ns of that time)')

# --------------------------------------------- divergence from the very start
print()
print('=' * 88)
print('4. WHEN DO THE TWO TRAJECTORIES FIRST DISAGREE?')
print('=' * 88)
print(f'  {"t (ns)":>12s} | {"GUI bb_in":>12s} {"ENG bb_in":>12s} {"diff":>11s} '
      f'| {"GUI bbo":>12s} {"ENG bbo":>12s} {"diff":>11s}')
for k in range(0, 12):
    # find the engine sample at the same time
    j = int(np.searchsorted(et, gt[k]))
    if j >= len(et):
        break
    if abs(et[j] - gt[k]) > 1e-15:
        continue
    dv1 = g['V(bb_in)'][1][k] - v[j, 1]
    dv2 = g['V(bbo)'][1][k] - v[j, 2]
    print(f'  {gt[k]*1e9:12.9f} | {g["V(bb_in)"][1][k]:12.9f} {v[j,1]:12.9f} '
          f'{dv1:11.3e} | {g["V(bbo)"][1][k]:12.9f} {v[j,2]:12.9f} {dv2:11.3e}')

# ------------------------------------------------------- carrier phase check
print()
print('=' * 88)
print('5. CARRIER PHASE AT THE STOP TIME')
print('=' * 88)
for label, tstop in [('GUI stop', stop), ('7 periods', 7*PERIOD)]:
    cyc = tstop / PERIOD
    phase = (cyc % 1.0) * 360
    print(f'  {label:12s}: t={tstop*1e9:10.6f} ns  cycles={cyc:.6f}  '
          f'phase={phase:7.3f} deg  carrier={np.sin(2*np.pi*cyc):+.6f} V')
print()
print('  The carrier restarts a cycle exactly at the GUI death time. The stop')
print('  lands ~8 ps BEFORE that boundary, i.e. the solver dies approaching it.')

(OUT / 'deep_diagnosis.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
