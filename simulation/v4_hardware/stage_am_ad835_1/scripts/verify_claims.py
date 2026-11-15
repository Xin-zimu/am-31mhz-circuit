"""Verify every quantitative claim made in the Stage AM-AD835.1 report."""
import sys, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rf_study as L

R = L.ROOT / 'results'


def g(n):
    return json.loads((R / f'{n}.json').read_text(encoding='utf8'))


def peak(v):
    return max(abs(v['min']), abs(v['max']))


print('=== claim: scheme A has Y/Z phase difference exactly 0 ===')
for n in ('A_nom', 'A470_nom', 'A560_nom', 'SA_510_680', 'SA_430_680', 'SA_390_620', 'SA_330_620'):
    j = g(n)
    print(f'  {n:14s} phZ={j["z_phase_relative_y_deg"]:+.2e}  ratio={j["z_y_amplitude_ratio"]:.6f}')

print('\n=== claim: A 330/680 Y peak 1.028 V > 1 V while Ypp only 1.730 ===')
j = g('A_nom')
print(f'  Ypp={j["y"]["vpp"]:.4f}  Ypeak={peak(j["y"]):.4f}  min={j["y"]["min"]:.4f} max={j["y"]["max"]:.4f}')

print('\n=== claim: 3.97 deg phase error costs only 0.12% in the vector sum ===')
A, Z = 0.877, 0.537
v0 = math.sqrt(A * A + Z * Z)
for d in (0.0, -3.966):
    print(f'  dphi={d:+7.3f} deg  |W|={math.sqrt(A*A + Z*Z + 2*A*Z*math.cos(math.radians(d))):.6f}')
print(f'  ratio = {math.sqrt(A*A + Z*Z + 2*A*Z*math.cos(math.radians(-3.966)))/v0:.6f} '
      f'-> {(math.sqrt(A*A + Z*Z + 2*A*Z*math.cos(math.radians(-3.966)))/v0 - 1)*100:.4f} %')

print('\n=== claim: 105 mV = 10 uA x 10.5 kOhm ===')
print(f'  {10e-6*10.5e3*1000:.3f} mV')

print('\n=== claim: 0.57 us of a 5 us pulse = 11.4 % ===')
print(f'  {0.57/5*100:.2f} %')

print('\n=== claim: 60 uA x 37.5 kOhm = 2.25 V (matches float_10n) ===')
print(f'  product = {60e-6*37.5e3:.4f} V ; float_10n meas = {g("float_10n")["y"]["dc"]:.4f} V')

print('\n=== claim: TP2 rises 68 % when load goes 2k//10p -> 37.5k//4p ===')
a, b = g('load_2k_10p')['out']['vpp'], g('load_37k5_4p')['out']['vpp']
print(f'  {a:.4f} -> {b:.4f} = {(b-a)/a*100:+.2f} %')

print('\n=== claim: B + double buffer = 46.6 mW, /0.85 = ~55 mW ===')
tb = g('B_Z06_nom')['supply_mw'] - g('load_2k_10p')['supply_mw']
bb = g('bb_prepost_a4_d10')
tg = bb['positive_extra_mw'] + bb['negative_extra_mw']
print(f'  B delta = {tb:.3f} ; baseband double-buffer = {tg:.3f} ; sum = {tb+tg:.3f} ; /0.85 = {(tb+tg)/0.85:.2f}')

print('\n=== claim: every load point has last-window drift < 1.3e-6 ===')
worst = 0
for n in ('load_500_4p', 'load_600_4p', 'load_700_4p', 'load_800_4p', 'load_900_4p',
          'load_1k_4p', 'load_2k_4p', 'load_2k_10p', 'load_3k3_4p', 'load_10k_4p',
          'load_37k5_4p', 'load_50k_4p', 'load_100k_4p'):
    d = g(n)['last_window_drift']
    worst = max(worst, d)
    flag = '  <-- exceeds 1.3e-6' if d > 1.3e-6 else ''
    print(f'  {n:14s} {d:.3e}{flag}')
print(f'  worst = {worst:.3e}')

print('\n=== claim: Y DC stays within +/-85 mV under +/- stress ===')
for n in ('A470_nom', 'A470_stress_pp', 'A470_stress_nn',
          'C_B_nom', 'C_B_stress_pn', 'C_B_stress_np'):
    j = g(n)
    print(f'  {n:16s} Ydc={j["y"]["dc"]*1000:+8.3f} mV  Zdc={j["z"]["dc"]*1000:+8.3f} mV  Ypk={peak(j["y"]):.4f}')

print('\n=== claim: only the 330/680 point exceeds +/-1 V among scheme-A sizings ===')
for n in ('A_nom', 'SA_330_620', 'SA_390_620', 'SA_390_680', 'SA_430_680',
          'A470_nom', 'SA_470_620', 'SA_510_680', 'A560_nom', 'SA_560_680'):
    p = peak(g(n)['y'])
    print(f'  {n:14s} Ypk={p:.4f} {"EXCEEDS" if p > 1.0 else ""}')

print('\n=== claim: modulation is 24.77 % regardless of attenuation (conv A) ===')
ar = json.loads((R / 'envelope_arithmetic.json').read_text(encoding='utf8'))
for e in ar:
    if e['convention'] == 'A':
        print(f'  {e["label"]:16s} Yp={e["Y_peak"]:.3f} Wh={e["W_high_vpp"]:.3f} '
              f'Wl={e["W_low_vpp"]:.3f} m={e["modulation"]:.4f} %')
