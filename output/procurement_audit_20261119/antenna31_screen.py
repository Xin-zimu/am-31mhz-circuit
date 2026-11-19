"""NEC2 feasibility screen, not a validated ABBREE product model."""
import sys, json, math, csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SOURCE = BASE / 'simulation/v4_hardware/stage_am_alt3_3_20261117'
sys.path.insert(0, str(SOURCE))
import nec_support as nec

OUT = Path(__file__).resolve().parent / 'antenna31_screen'
OUT.mkdir(exist_ok=True)
nec.RUN = OUT / 'runs'
nec.RUN.mkdir(exist_ok=True)
nec.EXE = BASE / 'simulation/v4_hardware/stage_am_alt3_1_20261116/tools/nec2c.exe'
W = 2 * math.pi * 31e6

def cards(length, freq, n=60, nrad=8, radial=.5):
    height = .83
    result = [nec.gw(1, n, (0,0,height), (0,0,height+length), .0015)]
    for k in range(nrad):
        a = 2*math.pi*k/nrad
        result.append(nec.gw(k+2, max(4,round(n*radial/length)), (0,0,height),
                             (radial*math.cos(a), radial*math.sin(a), height)))
    result += ['GE 0', 'GN 2 0 0 0 13 .005', 'LD 5 1 0 0 1.4e6']
    result += ['LD 5 %d 0 0 5.8e7' % t for t in range(2,nrad+2)]
    return result + ['FR 0 1 0 0 %g' % freq, 'EX 0 1 1 0 1 0', 'XQ']

def solve(length, freq, n=60, nrad=8, radial=.5):
    name = 'l%.6f_f%.3f_n%d_r%d_%.2f' % (length,freq,n,nrad,radial)
    return nec.solve(name, cards(length,freq,n,nrad,radial))

def root(coil, n=60, nrad=8, radial=.5):
    lo, hi = .5, 1.3
    def x(length):
        return solve(length,31,n,nrad,radial)['X'] + W*coil
    xa, xb = x(lo), x(hi)
    if xa*xb > 0:
        return None
    for _ in range(11):
        mid = (lo+hi)/2
        if x(mid)>0: hi=mid
        else: lo=mid
    length=(lo+hi)/2
    result=solve(length,31,n,nrad,radial)
    return dict(length_cm=length*100, residual_X_ohm=result['X']+W*coil,
                bare_R_ohm=result['R'])

cal=solve(1.3,27)
coil=-cal['X']/(2*math.pi*27e6)
results=[]
for factor in [.8,.9,1,1.1,1.2]:
    point=root(coil*factor)
    results.append(dict(coil_factor=factor, coil_uH=coil*factor*1e6, **(point or {})))
    print(results[-1], flush=True)
convergence=[dict(segments=n, **root(coil,n=n)) for n in [40,80]]
counterpoise=[dict(radials=nr,radial_cm=rl*100, **(root(coil,nrad=nr,radial=rl) or {}))
              for nr,rl in [(4,.5),(4,.25)]]
rows=[]
for cm in [70,80,90,100]:
    z=solve(cm/100,31)
    rows.append(dict(length_cm=cm, R_bare_ohm=z['R'], X_loaded_ohm=z['X']+W*coil))
data=dict(assumptions=['130cm straight uniform 3mm diameter steel radiator',
    'single ideal fixed series loading inductor, calibrated to X=0 at 27MHz at 130cm',
    'eight 50cm copper radials, height83cm above soil er13 sigma.005S/m',
    'no internal coil self-capacitance, transformer, feed cable, housing or contact model',
    'sensitivity is illustrative, not statistical confidence or actual component tolerance',
    'resonance does not establish 50ohm match, efficiency, bandwidth or 6m link'],
    inferred_coil_uH=coil*1e6, nominal=results[2], coil_sensitivity=results,
    convergence=convergence, changed_counterpoise_same_coil=counterpoise, lengths=rows)
(OUT/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False,indent=2))
