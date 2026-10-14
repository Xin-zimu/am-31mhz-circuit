"""Produce an evidence summary; numerical simulation is not wireless scoring."""
from pathlib import Path
import json
import numpy as np

HERE=Path(__file__).resolve().parent
rows=[]
for run in ['nominal_1ms','nominal_5ms']:
    file=HERE/f'{run}_metrics.json'
    if not file.exists(): continue
    d=json.loads(file.read_text(encoding='utf-8'))
    tail=d['last_five_cycles']; out=d['output_cycles_in_last_300us']
    row={'run':run,'points':d['points'],'t_end_ms':d['t_end_s']*1000,
         'frequency_V1_hz':float(np.mean([r['frequency_hz'] for r in tail])),
         'duty_V1_percent':float(np.mean([r['input_duty_percent'] for r in tail])),
         'frequency_V2_hz':float(np.mean([r['frequency_hz'] for r in out])),
         'duty_V2_percent':float(np.mean([r['duty_percent'] for r in out if r['duty_percent'] is not None])),
         'V2_mean_V':float(np.mean([r['V(v2)']['mean_v'] for r in tail])),
         'V2_robust_vpp':float(np.mean([r['V(v2)']['robust_vpp'] for r in tail])),
         'V2_raw_vpp':float(np.mean([r['V(v2)']['raw_vpp'] for r in tail])),
         'gain_robust':float(np.mean([r['robust_gain'] for r in tail])),
         'repeatability':d['repeatability_screen'],
         'linear_half_amplitude_test':'NOT_RUN',
         'cold_start_test':'NOT_RUN',
         'wireless_physical_acceptance':'NOT_TESTED',
         'scope':'Full functional model, precharged IC, native XSPICE command entry, not a new GUI run'}
    row['numerical_threshold_checks']={
        'V1_frequency_within_1pct':all(abs(r['frequency_hz']/20000-1)<=.01 for r in tail),
        'V2_frequency_within_1pct':all(abs(r['frequency_hz']/20000-1)<=.01 for r in out),
        'V1_duty50_within_5pp':all(abs(r['input_duty_percent']-50)<=5 for r in tail),
        'V2_duty50_within_5pp':all(r['duty_percent'] is not None and abs(r['duty_percent']-50)<=5 for r in out),
        'V2_ge_4V_at_4V_input_robust':all(r['V(v2)']['robust_vpp']>=4 for r in tail)}
    rows.append(row)
(HERE/'nominal_summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
