"""A-E postprocessing, extended sensitivity and explicit saturation diagnostics."""
import json
import math
from pathlib import Path
import numpy as np
from closure_metrics import analyse,read_raw,weights

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'round2_20261116'

def sensitivity():
    # Existing nine on-resonance calculations are inputs, not new evidence.
    prior=json.loads((ROOT/'results/closure_review.json').read_text(encoding='utf-8'))['matching']
    w=2*np.pi*31e6; rows=[]
    for c in np.linspace(6,12,25):
        for q in (30,60,100):
            l=1/w**2/(c*1e-12); rs=w*l/q
            for dc in (-.03,0,.03):
                for dl in (-.01,0,.01):
                    for cp in (0,.25,.5,1):
                        zcoil=complex(rs,w*l*(1+dl))
                        zcoil=1/(1/zcoil+1j*w*cp*1e-12)
                        z=15.224+zcoil+1/(1j*w*c*(1+dc)*1e-12)
                        rows.append(dict(C_pF=float(c),Q=q,C_error=dc,L_error=dl,Cp_pF=cp,
                            current_ratio_fixed_voltage=(15.224+rs)/abs(z),
                            V_for_5p3_mA_rms_mV=5.30*abs(z)))
    out=dict(existing_nine_cases=prior,new_grid_points=len(rows),
        model='Fixed-voltage sensitivity only; series coil R and L shunted by Cp; antenna+ground 5.224 ohm and sense10 ohm. Not driver capability.',
        rows=rows)
    (OUT/'results/a_sensitivity.json').write_text(json.dumps(out,indent=2)+'\n')
    summary=[]
    for cp in (0,.25,.5,1):
        subset=[r for r in rows if r['Cp_pF']==cp]
        summary.append(dict(Cp_pF=cp,minimum_current_ratio=min(r['current_ratio_fixed_voltage'] for r in subset),maximum_required_mV=max(r['V_for_5p3_mA_rms_mV'] for r in subset)))
    (OUT/'results/a_summary.json').write_text(json.dumps(summary,indent=2)+'\n')

def harmonics(t,x,f):
    phase=2*np.pi*f*(t-t[0]); cols=[np.ones(len(t))]
    for n in range(1,6): cols.extend([np.sin(n*phase),np.cos(n*phase)])
    a=np.column_stack(cols); w=weights(t); w=w/w.sum()
    b=np.linalg.solve(a.T@(w[:,None]*a),a.T@(w*x))
    amp=np.hypot(b[1::2],b[2::2])/np.sqrt(2)
    return dict(dc=float(b[0]),fundamental_rms=float(amp[0]),thd_2_to_5_pct=float(np.linalg.norm(amp[1:])/amp[0]*100))

def diagnose(path,base):
    d=read_raw(path); t=d['time']; a,b=base['window_s']; select=(t>=a)&(t<=b)
    d={k:x[select] for k,x in d.items()}; t=d['time']
    v1=d['v(v1)']; threshold=(np.quantile(v1,.05)+np.quantile(v1,.95))/2
    high=v1>threshold; cuts=np.r_[0,np.flatnonzero(np.diff(high.astype(int)))+1,len(t)-1]
    data={'high':[],'low':[]}
    for first,last in zip(cuts[:-1],cuts[1:]):
        keep=(t>t[first]+4e-6)&(t<t[last]-4e-6)
        if keep.sum()<100: continue
        tt=t[keep]; w=weights(tt); w=w/w.sum()
        bc=d['v(drv_b)'][keep]-d['v(drv_c)'][keep]
        be=d['v(drv_b)'][keep]-d['v(drv_e)'][keep]
        spec={k:harmonics(tt,d[k][keep],base['carrier_Hz']) for k in ['v(tp3)','v(drv_b)','v(drv_c)','v(ef_e)','i(ltune)']}
        xx=d['i(ltune)'][keep]
        z=np.flatnonzero((xx[:-1]<0)&(xx[1:]>=0))
        tz=tt[z]-xx[z]*(tt[z+1]-tt[z])/(xx[z+1]-xx[z])
        period=np.polyfit(np.arange(len(tz)),tz-tz[0],1)[0]
        row=dict(QCE_bc_max_V=float(max(bc)),QCE_be_min_V=float(min(be)),
            carrier_from_zero_crossing_regression_Hz=float(1/period),
            QCE_min_VCE_V=float(min(d['v(drv_c)'][keep]-d['v(drv_e)'][keep])),
            fraction_bc_positive_be_positive=float(w@((bc>0)&(be>0))),
            fraction_bc_above_0p1=float(w@(bc>.1)),
            QCE_mean_ic_mA=float(w@d['i(@qce[ic])'][keep]*1e3) if 'i(@qce[ic])' in d else None,
            ce_fundamental_gain=spec['v(drv_c)']['fundamental_rms']/spec['v(drv_b)']['fundamental_rms'],
            total_transconductance_A_per_V=spec['i(ltune)']['fundamental_rms']/spec['v(tp3)']['fundamental_rms'],spectra=spec)
        data['high' if high[first] else 'low'].append(row)
    gain={state:float(np.median([r['ce_fundamental_gain'] for r in rows])) for state,rows in data.items()}
    wt=weights(t); wt=wt/wt.sum()
    vce=d['v(drv_c)']-d['v(drv_e)']; bc=d['v(drv_b)']-d['v(drv_c)']; be=d['v(drv_b)']-d['v(drv_e)']
    sat=(bc>0)&(be>0); idx=int(np.argmin(vce))
    transitions=t[cuts[1:-1]]
    dist=float(t[idx]-transitions[np.argmin(abs(transitions-t[idx]))])
    change=np.diff(np.r_[False,sat,False].astype(int)); starts=np.flatnonzero(change==1); ends=np.flatnonzero(change==-1)
    longest=max((t[min(e,len(t)-1)]-t[a] for a,e in zip(starts,ends)),default=0)
    current=d['i(ltune)']; zc=np.flatnonzero((current[:-1]<0)&(current[1:]>=0))
    period=np.diff(t[zc]); valid=(period>.7/base['carrier_Hz'])&(period<1.3/base['carrier_Hz'])
    peaks=np.array([max(abs(current[a:b+1])) for a,b in zip(zc[:-1],zc[1:])])[valid]
    tc=((t[zc[:-1]]+t[zc[1:]])/2)[valid]
    edge_metrics=[]
    for k in cuts[1:-1]:
        after=high[k]; target=base['high_plateau_median_peak_mA' if after else 'low_plateau_median_peak_mA']/1e3
        use=(tc>t[k])&(tc<t[k]+8e-6); ts=tc[use]; pk=peaks[use]
        bad=abs(pk/target-1)>.02
        settling=float(ts[np.flatnonzero(bad)[-1]]-t[k]) if np.any(bad) else 0
        edge_metrics.append(dict(edge='rise' if after else 'fall',minimum_complete_cycle_peak_mA=float(min(pk)*1e3),maximum_complete_cycle_peak_mA=float(max(pk)*1e3),last_outside_2pct_us=settling*1e6,observation_window_us=8))
    return dict(plateaus=data,ce_gain_high_vs_low_dB=float(20*np.log10(gain['high']/gain['low'])),
        transition_diagnostics=dict(saturation_time_fraction=float(wt@sat),maximum_VBC_V=float(max(bc)),minimum_VCE_offset_from_nearest_edge_us=dist*1e6,longest_contiguous_saturation_ns=float(longest*1e9),edge_metrics=edge_metrics,
            at_minimum_VCE={k:float(d[k][idx]) for k in ['time','v(tp3)','v(drv_b)','v(drv_e)','v(drv_c)','v(ef_e)','i(@qce[ic])','i(@qef[ic])']}),
        interpretation='Gain ratio across two AM plateaus, not a small-signal P1dB sweep. BC/BE simultaneous forward bias plus gain change and THD diagnose saturation/compression.')

def process(name):
    path=OUT/'results'/f'{name}.raw'
    base=analyse(path)
    cases=json.loads((OUT/'cases.json').read_text())
    base['assumptions']=cases[name]
    result={'case':cases[name],'metrics':base,'diagnostics':diagnose(path,base)}
    (OUT/'results'/f'{name}_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        for name in sys.argv[1:]:
            result=process(name)
            print(name,json.dumps(result['metrics']),flush=True)
    else:
        sensitivity(); print('A sensitivity grid complete')
