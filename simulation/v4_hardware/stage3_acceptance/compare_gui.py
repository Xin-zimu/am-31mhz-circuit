"""Compare measured GUI cycles with matching-time command-interface evidence."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent

def summary(d):
    tail=d['last_five_cycles']; out=d['output_cycles_in_last_300us']
    return {'V1_frequency_hz':float(np.mean([r['frequency_hz'] for r in tail])),
            'V1_duty_percent':float(np.mean([r['input_duty_percent'] for r in tail])),
            'V2_frequency_hz':float(np.mean([r['frequency_hz'] for r in out])),
            'V2_duty_percent':float(np.mean([r['duty_percent'] for r in out])),
            'V1_robust_vpp':float(np.mean([r['V(v1)']['robust_vpp'] for r in tail])),
            'V2_robust_vpp':float(np.mean([r['V(v2)']['robust_vpp'] for r in tail])),
            'V2_raw_vpp':float(np.mean([r['V(v2)']['raw_vpp'] for r in tail])),
            'V2_mean_V':float(np.mean([r['V(v2)']['mean_v'] for r in tail])),
            'gain_robust':float(np.mean([r['robust_gain'] for r in tail]))}

gui=json.loads((H/'S03_GUI_2ms_V4_3_metrics.json').read_text(encoding='utf-8'))
eng=json.loads((H/'engine_reference_2ms_metrics.json').read_text(encoding='utf-8'))
gs,es=summary(gui),summary(eng)
result={'gui':gs,'engine_same_time_window':es,
        'absolute_differences':{k:gs[k]-es[k] for k in gs},
        'gui_repeatability_screen':gui['repeatability_screen'],
        'scope':'2 ms native GUI reproduction, user authorized shorter window; 5 ms GUI attempt failed from memory shortage.'}
result['engineering_comparison_limits']={'frequency_relative':.001,'duty_percentage_points':.1,'amplitude_relative':.001,'bias_V':.01,'official_acceptance':False}
result['comparison_passes']=bool(
    all(abs(gs[k]/es[k]-1)<.001 for k in ['V1_frequency_hz','V2_frequency_hz','V1_robust_vpp','V2_robust_vpp'])
    and all(abs(gs[k]-es[k])<.1 for k in ['V1_duty_percent','V2_duty_percent'])
    and abs(gs['V2_mean_V']-es['V2_mean_V'])<.01)
(H/'gui_engine_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
z=np.load(H/'S03_GUI_2ms_V4_3.npz'); a=z['data']; names=list(z['names'])
fig,ax=plt.subplots(2,1,figsize=(11,6),layout='constrained')
for name,color in [('V(v1)','#167c80'),('V(v2)','#db6d28')]:
    i=names.index(name)
    sel=a[:,0]>=.0017
    ax[0].plot(a[sel][::8,0]*1e3,a[sel][::8,i],label=name,color=color,lw=1)
ax[0].set(xlabel='Time (ms)',ylabel='Voltage (V)',title='Native Multisim GUI: final 300 us of 2 ms run')
for label,d,color in [('GUI',gui,'#db6d28'),('Engine',eng,'#167c80')]:
    rows=d['last_five_cycles']
    ax[1].plot([r['start_s']*1e3 for r in rows],[r['V(v2)']['mean_v'] for r in rows],'.-',label=label,color=color)
ax[1].set(xlabel='Cycle start (ms)',ylabel='V2 mean (V)',title='Last five complete input cycles: bias comparison')
for v in ax:v.grid(alpha=.2);v.legend()
fig.savefig(H/'S03_GUI_2ms_comparison.png',dpi=160)
print(json.dumps(result,indent=2))
