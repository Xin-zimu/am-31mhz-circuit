"""S05-08: blocking metric, checksum audit and the report table.

Delta_20k = 20log10(|C20k,disturbed| / |C20k,clean|), the definition fixed in
S05-05/S05-06.  Square waves are normalised against the square-wave reference,
never against the sine reference.
"""
from pathlib import Path
import json, sys, hashlib
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE/'results'
NET = HERE/'netlists'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rec(name):
    return json.loads((RESULTS/(name+'.json')).read_text(encoding='utf-8'))


CASES = ['T_sq50_six', 'T_sq10_six', 'T_sine_clean', 'T_sine_29_10', 'T_sine_29_50',
         'T_sine_33_10', 'T_sine_33_40', 'T_sq10_29_10', 'T_sq50_33_10',
         'T_sq50_Q40_six', 'T_sq50_TOL_retuned', 'T_sq50_TOL_held',
         'T_sq50_Ac20', 'T_sq10_Ac20',
         'T_sq50_QFLOOR_six', 'T_sq10_QFLOOR_six',
         'T_sq50_TOL_0p95_0p95_six', 'T_sq50_TOL_1p05_1p05_six']

rows = []
audit = dict(checked=[], missing=[], hash_mismatch=[])
for name in CASES:
    p = RESULTS/(name+'.json')
    if not p.exists():
        audit['missing'].append(name); continue
    r = rec(name)
    ok = (sha(NET/(r['name']+'.cir')) == r['net_sha256']
          and sha(r['raw_path']) == r['raw_sha256']
          and sha(RESULTS/(r['name']+'.log')) == r['log_sha256'])
    (audit['checked'] if ok else audit['hash_mismatch']).append(name)
    f = r['metrics']['final']
    rows.append(dict(name=name, wave=('square' if 'sq' in name else 'sine'),
                     ac_mv=1000*r['config'].get('ac', .01),
                     peak20=f.get('peak20'), robust_vpp=f.get('robust_vpp'),
                     vpp=f.get('vpp'), duty=f.get('duty_pct'),
                     frequency=f.get('frequency_hz'), low=f.get('low'), high=f.get('high'),
                     rail_fraction=f.get('rail_fraction'),
                     front=r.get('front_end', {}).get('params', {}).get('part', '132-17L'),
                     blockers=r['config'].get('blockers', []),
                     elapsed=r.get('elapsed_s')))

by = {r['name']: r for r in rows}
REF = {'sine': 'T_sine_clean', 'sq10': 'T_sq10_six', 'sq50': 'T_sq50_six'}


def delta(name, ref):
    a, b = by.get(name), by.get(REF[ref])
    if a is None or b is None:
        return None
    return float(20*np.log10(abs(a['peak20'])/abs(b['peak20'])))


blocking = []
for name, ref in [('T_sine_29_10', 'sine'), ('T_sine_29_50', 'sine'),
                  ('T_sine_33_10', 'sine'), ('T_sine_33_40', 'sine'),
                  ('T_sq10_29_10', 'sq10'), ('T_sq50_33_10', 'sq50')]:
    blocking.append(dict(case=name, reference=REF[ref],
                         delta20k_db=delta(name, ref),
                         reference_peak20=by[REF[ref]]['peak20'],
                         case_peak20=(by.get(name) or {}).get('peak20'),
                         duty_valid=ref.startswith('sq')))

summary = dict(
    definition='Delta20k = 20log10(|C20k,disturbed|/|C20k,clean|); negative = loss',
    nominal_gain31_v_v=41.2126,
    rows=rows, blocking=blocking, audit=audit,
    note='10 mV / 50 ohm source, 31 MHz, m=0.5, 20 kHz; blockers are open-circuit peak at 29/33 MHz')
json.dump(summary, open(HERE/'chain_summary.json', 'w', encoding='utf-8'),
          indent=2, ensure_ascii=False)

for r in rows:
    print('%-20s %-6s vpp=%7.3f duty=%6s f=%8s p20=%.4f' %
          (r['name'], r['wave'], r['vpp'],
           'n/a' if r['duty'] is None else round(r['duty'], 2),
           'n/a' if r['frequency'] is None else round(r['frequency']), r['peak20']))
print()
for b in blocking:
    d = b['delta20k_db']
    print('%-16s %+.3f dB' % (b['case'], d) if d is not None else b['case'] + ' n/a')
print('\naudit: checked %d, missing %d, mismatch %d' %
      (len(audit['checked']), len(audit['missing']), len(audit['hash_mismatch'])))
