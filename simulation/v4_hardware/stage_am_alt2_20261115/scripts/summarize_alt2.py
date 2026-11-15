"""Summaries and transparent finite-step frequency comparison; no simulations."""
import csv,json
import numpy as np
from alt2 import ROOT,core,bbmetrics
from edges import envelope

rows=[]
for p in sorted((ROOT/'results').glob('*.json')):
    d=json.loads(p.read_text(encoding='utf8'))
    if not isinstance(d,dict) or 'rf' not in d:continue
    name=d['name'];rf=d['rf'];kw=d['settings'];ps=rf['plateaus']
    edgefile=ROOT/'results'/f'{name}_edges.json'
    ed=json.loads(edgefile.read_text()) if edgefile.exists() else None
    row={'name':name,'full_c4':bool(kw.get('full')),'amp_setting':kw.get('amp',4),
         'duty_setting_pct':100*kw.get('duty',.5),'pot_top_ohm':kw.get('pot'),
         'v1_vpp':d['v1']['vpp'],'v1_high':d['v1']['high'],'v1_low':d['v1']['low'],
         'v1_freq_hz':d['v1']['freq_hz'],'v1_duty_pct':d['v1']['duty_pct'],
         'v3_high_fund_vpp':rf['v3_high_fund_vpp'],'v3_low_fund_vpp':rf['v3_low_fund_vpp'],
         'm':rf['modulation_index'],'step_fund_vpp':rf['envelope_step_fund_vpp'],
         'v3_f_min_hz':min(x['v3_frequency_hz'] for x in ps),'v3_f_max_hz':max(x['v3_frequency_hz'] for x in ps),
         'thd_max_pct':max(x['v3']['thd_h2_h5_pct'] for x in ps),
         'vce_min':rf['entire_window_vce_min'],'vcb_min':rf['entire_window_vcb_min'],
         'ic_low_ma':float(np.mean([x['ic_est_ma'] for x in ps if not x['high']])),
         'ic_high_ma':float(np.mean([x['ic_est_ma'] for x in ps if x['high']])),
         'i_rf_ma':d['i_rf_ma'],'i_bb_ma':d['i_bb_ma'],
         'pbat_9v_iq8ma_budget_mw':9*(d['i_rf_ma']+d['i_bb_ma']+8) if kw.get('full') else None,
         'overshoot_step_pct':ed['max_overshoot_step_pct'] if ed else None,
         'reverse_step_pct':ed['max_reverse_step_pct'] if ed else None,
         'tilt_step_pct':ed['max_abs_tilt_step_pct'] if ed else None,
         'transition_10_90_ns_max':max((x['transition_10_90_ns'] for x in ed['edges'] if x['transition_10_90_ns'] is not None),default=None) if ed else None,
         'settle_2pct_step_us_max':max((x['settle_2pct_step_us'] for x in ed['edges'] if x['settle_2pct_step_us'] is not None),default=None) if ed else None,
         'unsettled_edges':sum(x['settle_2pct_step_us'] is None for x in ed['edges']) if ed else None}
    if kw.get('full'):
        raw=core.read_raw(ROOT/'results'/f'{name}.raw');tc,env,*_=envelope(raw)
        row['v3_envelope_duty_pct']=bbmetrics({'time':tc,'v(vm)':env})['duty_pct']
    else:row['v3_envelope_duty_pct']=None
    rows.append(row)
(ROOT/'results/summary.json').write_text(json.dumps(rows,indent=2))
with (ROOT/'results/summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
matrix=[r for r in rows if r['name'].startswith('full_a')]
matrix.sort(key=lambda x:(x['amp_setting'],x['duty_setting_pct']))
md=['# AM-ALT.2 实际 C4＋LM393 组合测量','',
    '全部为仿真，测试夹具10kΩ∥5pF。精密阻值是模型校准位置，实物按v1实测回调。',
    '', '|设定Vpp|占空比设定%|实测v1 Vpp|实测频率Hz|实测占空比%|v3高/低Vpp|m%|包络过冲/阶跃%|',
    '|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in matrix:
    md.append(f"|{r['amp_setting']}|{r['duty_setting_pct']:.0f}|{r['v1_vpp']:.6f}|{r['v1_freq_hz']:.2f}|{r['v1_duty_pct']:.4f}|{r['v3_high_fund_vpp']:.6f}/{r['v3_low_fund_vpp']:.6f}|{r['m']*100:.3f}|{r['overshoot_step_pct']:.3f}|")
(ROOT/'results/matrix_table.md').write_text('\n'.join(md)+'\n',encoding='utf8')
lookup={r['name']:r for r in rows}
names=['full_a4_d50','fine_a4_d50_h025','fine_a4_d50_h0125']
if all(n in lookup for n in names):
    ns=np.array([.5,.25,.125]);fs=np.array([(lookup[n]['v3_f_min_hz']+lookup[n]['v3_f_max_hz'])/2 for n in names])
    a,b,c=fs
    result={'names':names,'tmax_ns':ns.tolist(),'frequency_mid_hz':fs.tolist(),
            'successive_shift_ratio':float((b-a)/(c-b)),
            'h2_extrapolated_hz_using_coarse_pair':float((4*b-a)/3),
            'h2_extrapolated_hz_using_fine_pair':float((4*c-b)/3),
            'extrapolation_is_not_measured_frequency':True,
            'VH_relative_change_fine_vs_coarse_pct':100*(lookup[names[-1]]['v3_high_fund_vpp']/lookup[names[0]]['v3_high_fund_vpp']-1),
            'VL_relative_change_fine_vs_coarse_pct':100*(lookup[names[-1]]['v3_low_fund_vpp']/lookup[names[0]]['v3_low_fund_vpp']-1)}
    diagnostic=[]
    for name,freq in zip(names,fs):
        raw=core.read_raw(ROOT/'results'/f'{name}.raw');dt=np.diff(raw['time'])
        heff2=float(np.sum(dt**3)/np.sum(dt))
        diagnostic.append({'name':name,'time_weighted_h_eff_ns':np.sqrt(heff2)*1e9,
                           'linear_trap_phase_corrected_hz_estimate':float(freq*(1+(2*np.pi*freq)**2*heff2/12))})
    result['linear_oscillator_phase_error_diagnostic_not_hardware_measurement']=diagnostic
    (ROOT/'results/frequency_step_check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
print('RF cases:',len(rows),'Full matrix:',len(matrix))
for r in matrix:print(r['name'],round(r['v1_vpp'],6),round(r['overshoot_step_pct'],3),round(r['pbat_9v_iq8ma_budget_mw'],3))
