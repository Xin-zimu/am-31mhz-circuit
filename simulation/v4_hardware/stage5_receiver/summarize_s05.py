"""Build compact evidence from immutable simulation results, including rejected cases."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_s05 import HERE, ROOT, readraw, sha

def get(n):return json.loads((HERE/'results'/(n+'.json')).read_text())
def met(n):return get(n)['metrics']
def delta(a,b,key):return (met(b)[key]/met(a)[key]-1)*100

results=[json.loads(p.read_text()) for p in sorted((HERE/'results').glob('*.json'))]
summary=dict(date='2026-10-29',runs=len(results),
    transient_runs=sum('out_envelope_vpp' in r['metrics'] for r in results),
    ac_runs=sum('gain_31mhz' in r['metrics'] for r in results),
    noise_runs=sum('noise_factor_db_31mhz' in r['metrics'] for r in results),
    r1_amplitude_step_change_pct=delta('r1_a0p01','r1_converge025','out_envelope_vpp'),
    r1_amplitude_longer_time_change_pct=delta('r1_a0p01','r1_tail600us','out_envelope_vpp'),
    r1_square_step_change_pp=met('r1_square_converge025')['duty_pct']-met('r1_d0p1')['duty_pct'],
    r1_half_modulation_linearity_error_pct=(met('r1_m0p25')['out_envelope_vpp']/(.5*met('r1_a0p01')['out_envelope_vpp'])-1)*100,
    r1_quarter_modulation_linearity_error_pct=(met('r1_m0p125')['out_envelope_vpp']/(.25*met('r1_a0p01')['out_envelope_vpp'])-1)*100,
    r1_baseband_gain_for_4p8vpp_estimate=4.8/met('r1_d0p5')['out_envelope_vpp'],
    r1_load10k_amplitude_change_pct=delta('r1_a0p01','r1_load10k','out_envelope_vpp'),
    r1_diode_stress_amplitude_change_pct=delta('r1_a0p01','r1_diode_stress','out_envelope_vpp'),
    sensitivity_accepted=False,wireless_range_accepted=False,bat85s_qualified=False,
    model_note='BAT85 manufacturer reference is discontinued; BAT85S procurement candidate not modeled as identical')
frozen=[ROOT/'simulation/v4_hardware/AM_20k_31MHz_V4_3_REPAIRED.ms14',ROOT/'simulation/v4_hardware/repair_20261011/final_actual.cir']
summary['frozen_hashes']={str(p.relative_to(ROOT)):sha(p) for p in frozen}
(HERE/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
fields=['name','ac','m','duty','amp','rs','rd','cd','rf','cf','load','temp','out_envelope_vpp','out_raw_vpp','out_robust_vpp','out_thd_2to10','out_rf_residual_rms','out_rf_residual_pp_max','duty_pct','supply_power_w']
with (HERE/'measurements.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in results:
        if 'out_envelope_vpp' not in r['metrics']:continue
        row=dict(name=r['name'],**r['config'],**r['metrics']);w.writerow({k:row.get(k) for k in fields})

plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':10,'axes.unicode_minus':False})
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
ar=[get('r1_a'+str(a).replace('.','p')) for a in [.0001,.001,.003,.005,.01,.015,.02,.04,.08]]
x=np.array([r['config']['ac']*1000 for r in ar])
axs[0,0].semilogx(x,[r['metrics']['out_envelope_vpp'] for r in ar],'o-',color='#126b8a')
axs[0,0].set(xlabel='源端载波峰值 Ac (mV，50 Ω 开路口径)',ylabel='恢复包络 Vpp (V)',title='R1 小信号至过载扫描（m=0.5）')
axs[0,1].semilogx(x,[100*r['metrics']['out_thd_2to10'] for r in ar],'o-',color='#c45b26')
axs[0,1].set(xlabel='源端载波峰值 Ac (mV)',ylabel='THD 2～10次谐波 (%)',title='40 / 80 mV 点出现明显非线性')
for n,label in [('r1_d0p1','10%'),('r1_d0p5','50%')]:
    r=get(n);d=readraw(Path(r['raw_path']));tt=np.linspace(200e-6,250e-6,8000)
    axs[1,0].plot((tt-200e-6)*1e6,np.interp(tt,d['time'],d['v(out)']),label=label)
axs[1,0].set(xlabel='时间 (µs)',ylabel='滤波输出 (V)',title='R1 方波恢复，Ac=10 mV；含载波残余')
axs[1,0].legend()
r=get('v2_rx_re22');d=readraw(Path(r['raw_path']));f=d['frequency'].real
axs[1,1].semilogx(f/1e6,20*np.log10(abs(d['v(rf)'])),color='#126b8a')
axs[1,1].axvline(31,color='#c45b26',linestyle='--',label='31 MHz')
axs[1,1].set(xlabel='频率 (MHz)',ylabel='小信号电压增益 (dB)',title='R1 宽频响应：仍缺接收选频',xlim=(.1,300),ylim=(-20,60))
axs[1,1].legend()
for ax in axs.ravel():ax.grid(alpha=.2)
fig.suptitle('S05 首批独立仿真 · ngspice 47 · 参考器件模型，非整机灵敏度验收',fontsize=14)
fig.savefig(HERE/'S05_first_batch.png',dpi=170)
plt.close(fig)

# Freeze a readable parameterized candidate, with independent output path.
src=HERE/'netlists/r1_a0p01.cir'
candidate=src.read_text().replace('D:/ms_xsp/s05_receiver_20261029/r1_a0p01.raw','S05_R1_candidate.raw')
(HERE/'S05_R1_candidate.cir').write_text(candidate,encoding='ascii')
manifest=[]
for r in results:
    p=Path(r['raw_path']); src=HERE/'netlists'/(r['name']+'.cir')
    assert sha(p)==r['raw_sha256'] and sha(src)==r['net_sha256'],r['name']
    manifest.append(dict(name=r['name'],net_sha256=r['net_sha256'],raw_sha256=r['raw_sha256'],raw_path=r['raw_path'],config=r['config']))
(HERE/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
