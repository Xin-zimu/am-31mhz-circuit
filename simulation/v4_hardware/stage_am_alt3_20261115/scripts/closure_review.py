"""Analytical design review, not bench data or a new transistor simulation."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
w = 2 * math.pi * 31e6
prior = json.loads((ROOT / 'results/final_verify.json').read_text(encoding='utf-8'))['fin_nom']
rows = []
for c in (6, 8.913, 12):
    l = 1 / (w*w*c*1e-12)
    for q in (30, 60, 100):
        r = 4.224 + 1 + w*l/q
        rows.append(dict(C_pF=c, L_uH=l*1e6, coil_Q_assumed=q,
                         R_without_sense_ohm=r,
                         V_required_without_sense_mV_rms=5.30*r,
                         V_required_with_sense_mV_rms=5.30*(r+10),
                         bandwidth_with_sense_kHz=(r+10)/(2*math.pi*l)/1e3))
z = 1/(1/10 + 1j*w*16e-12)
# Independent bounded errors: two capacitor tolerances, two frequency errors.
corners = []
import itertools
for t in (.0025, .01):
    errors = []
    for a,b,d,e in itertools.product((-1,1), repeat=4):
        l0=2.957e-6
        f1=1/(2*math.pi*math.sqrt(l0*((100*(1+a*t)+3)*1e-12)))
        f2=1/(2*math.pi*math.sqrt(l0*((220*(1+b*t)+3)*1e-12)))
        got=((2*math.pi*f1*(1+d*.001))**-2-(2*math.pi*f2*(1+e*.001))**-2)/(-120e-12)
        errors.append(100*(got/l0-1))
    corners.append(dict(cap_tolerance_pct=t*100, frequency_bound_pct=.1,
                        L_error_min_pct=min(errors), L_error_max_pct=max(errors)))
out = dict(design_only=True, bench_measurement_performed=False,
           status='已执行、勘误完成、待技术闭合',
           driver_previous_simulation=prior,
           coverage_ratio=[prior['i_ant_rms_mA']/5.30,prior['i_ant_rms_mA']/3.75],
           sense_impedance_ohm=dict(real=z.real,imag=z.imag,magnitude=abs(z)),
           capacitor_error_corners=corners,matching=rows,
           fixed_voltage_sense_estimate_mA=prior['i_ant_rms_mA']*13.824/23.824,
           caveat='Fixed-voltage estimate excludes driver output impedance and nonlinear load response; not a transistor simulation.')
assert 1.17 < out['coverage_ratio'][0] < 1.19
assert abs(abs(z)/10-1)<.001
assert max(abs(corners[0][k]) for k in ('L_error_min_pct','L_error_max_pct')) < 1.3
(ROOT/'results/closure_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
