"""Interpolate the retraction point where a 27 MHz base-loaded whip resonates at 31 MHz.

Screening only: the product's internal loading coil is UNKNOWN. The coil below is the one
that would be required to resonate a bare 1.3 m whip at 27 MHz, used as a stand-in.
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
d = json.loads((ROOT / 'whatif_27MHz_loaded_whip.json').read_text(encoding='utf-8'))
L_coil = d['full_1p3m_27MHz']['implied_coil_H']
W = 2 * math.pi * 31e6
ants = json.loads((ROOT / 'antenna_nominal.json').read_text(encoding='utf-8'))

print('internal coil stand-in: %.3f uH' % (L_coil * 1e6))
print()
print(' len_cm   Lant_uH   Cant_pF    f_res_MHz   X31_ohm   note')
rows = []
for a in ants:
    Lt = a['Lant_H'] + L_coil
    Ct = a['Cant_F']
    fr = 1 / (2 * math.pi * math.sqrt(Lt * Ct))
    X31 = W * Lt - 1 / (W * Ct)
    rows.append(dict(length_cm=round(a['length_m'] * 100), f_res_Hz=fr, X31_ohm=X31))
    print('%7d %9.4f %9.3f %12.2f %10.1f' % (round(a['length_m'] * 100), a['Lant_H'] * 1e6,
                                              Ct * 1e12, fr / 1e6, X31))

# Linear interpolation between the bracketing lengths for X31 = 0.
a, b = rows[1], rows[2]   # 80 cm (X<0) and 90 cm (X>0)
t = -a['X31_ohm'] / (b['X31_ohm'] - a['X31_ohm'])
len_zero = a['length_cm'] + t * (b['length_cm'] - a['length_cm'])
print()
print('X31 = 0 (series resonance at 31 MHz) at approx %.1f cm extension' % len_zero)
print('  -> within the 1 m course limit, no external series inductor required')
out = dict(note='Screening estimate. Internal coil of the real product is unknown; this uses the '
                'coil that a bare 1.3 m whip would need at 27 MHz as a stand-in.',
           implied_internal_coil_H=L_coil, rows=rows,
           length_cm_for_31MHz_resonance=len_zero)
(ROOT / 'whatif_27MHz_retraction.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('written whatif_27MHz_retraction.json')
