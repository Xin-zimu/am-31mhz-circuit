"""Time-weighted metrics for the 10-ohm preliminary run; no bench claims."""
import json
import re
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]

def read_raw(path):
    b = path.read_bytes()
    offset = b.index(b'Binary:\n') + len(b'Binary:\n')
    header = b[:offset].decode('latin1')
    nv = int(re.search(r'No\. Variables:\s+(\d+)', header)[1])
    n = int(re.search(r'No\. Points:\s+(\d+)', header)[1])
    names = re.findall(r'^\s*\d+\s+(\S+)\s+\S+\s*$', header.split('Variables:',1)[1], re.M)
    assert len(b)-offset == n*nv*8, 'Unexpected binary layout'
    a = np.frombuffer(b, dtype='<f8', offset=offset).reshape(n,nv)
    assert len(names)==nv and np.all(np.diff(a[:,0])>0)
    return dict(zip(names,a.T))

def weights(t):
    dt=np.diff(t)
    return np.r_[dt[0]/2,(dt[:-1]+dt[1:])/2,dt[-1]/2]

def fit(t,x,f):
    w=weights(t); w=w/w.sum()
    phase=2*np.pi*f*(t-t[0])
    a=np.column_stack((np.sin(phase),np.cos(phase),np.ones(len(t))))
    coeff=np.linalg.solve(a.T@(w[:,None]*a),a.T@(w*x))
    residual=float(np.sum(w*(x-a@coeff)**2))
    return float(np.hypot(*coeff[:2])/np.sqrt(2)),residual

def analyse(path):
    d=read_raw(path); t=d['time']; v=d['v(v1)']
    threshold=(np.quantile(v,.05)+np.quantile(v,.95))/2
    rising=np.flatnonzero((v[:-1]<threshold)&(v[1:]>=threshold))
    edge=t[rising]+(threshold-v[rising])/(v[rising+1]-v[rising])*(t[rising+1]-t[rising])
    assert len(edge)>=3, 'Need at least two complete modulation cycles'
    tw=np.r_[edge[0],t[(t>edge[0])&(t<edge[-1])],edge[-1]]
    d={k:np.interp(tw,t,x) for k,x in d.items()}; t=tw
    w=weights(t); w=w/w.sum(); x=d['i(ltune)']
    crossing=np.flatnonzero((x[:-1]<0)&(x[1:]>=0))
    ct=t[crossing]-x[crossing]*(t[crossing+1]-t[crossing])/(x[crossing+1]-x[crossing])
    seed=1/np.median(np.diff(ct))
    opt=minimize_scalar(lambda f:fit(t,x,f)[1],bounds=(seed-2000,seed+2000),method='bounded',options={'xatol':.01})
    carrier,residual=fit(t,x,opt.x)
    peaks=np.array([max(abs(x[a:b+1])) for a,b in zip(crossing[:-1],crossing[1:])])
    cycles=(ct[:-1]+ct[1:])/2
    vh=d['v(v1)']>threshold
    transitions=t[np.flatnonzero(np.diff(vh.astype(int)))+1]
    distance=np.min(abs(cycles[:,None]-transitions[None,:]),axis=1)
    valid=(distance>3e-6)&(cycles>t[0]+3e-6)&(cycles<t[-1]-3e-6)
    high=np.interp(cycles,t,d['v(v1)'])>threshold
    hp=float(np.median(peaks[valid&high])); lp=float(np.median(peaks[valid&~high]))
    # Fit each contiguous plateau separately: never integrate across masked gaps.
    bounds=np.r_[t[0],transitions,t[-1]]
    plateau_fits={'high':[],'low':[]}
    for left,right in zip(bounds[:-1],bounds[1:]):
        keep=(t>left+3e-6)&(t<right-3e-6)
        if keep.sum()<100:
            continue
        label='high' if np.median(d['v(v1)'][keep])>threshold else 'low'
        amp,_=fit(t[keep],x[keep],opt.x)
        plateau_fits[label].append(amp*1e3)
    rf=-float(w@d['i(vsup)']); bb=-float(w@d['i(v5)'])
    out=dict(design_only=True, measured_antenna_parameters=False,
        window_s=[float(t[0]),float(t[-1])],modulation_cycles=len(edge)-1,
        carrier_Hz=float(opt.x),carrier_fit_success=bool(opt.success),
        total_time_weighted_rms_mA=float(np.sqrt(w@(x*x))*1e3),
        carrier_fundamental_rms_mA=carrier*1e3,
        high_plateau_median_peak_mA=hp*1e3,low_plateau_median_peak_mA=lp*1e3,
        high_plateau_sine_equivalent_rms_mA=hp/np.sqrt(2)*1e3,
        high_plateau_fundamental_rms_mA=float(np.median(plateau_fits['high'])),
        low_plateau_fundamental_rms_mA=float(np.median(plateau_fits['low'])),
        plateau_fundamental_rms_samples_mA=plateau_fits,
        full_window_peak_mA=float(max(abs(x))*1e3),
        modulation_index=(hp-lp)/(hp+lp),
        minimum_QCE_VCE_V=float(min(d['v(drv_c)']-d['v(drv_e)'])),
        minimum_QEF_VCE_V=float(min(d['v(vcc)']-d['v(ef_e)'])),
        rf_supply_average_mA=rf*1e3,baseband_supply_average_mA=bb*1e3,
        simulated_supply_power_mW=float(-w@(d['v(vcc)']*d['i(vsup)']+d['v(v5)']*d['i(v5)'])*1e3),
        battery_budget_mW=9*(rf+bb+.008)*1e3,
        sense_resistor_power_mW=float(w@(x*x)*10*1e3),
        assumptions='Nominal 8.913 pF, 2.9572 uH, 14.824 ohm antenna+coil+ground, 10 ohm sensing; 9 V battery, linear regulators, 8 mA regulator ground current.',
        metric_notes='Carrier: time-weighted sine/cosine/DC least-squares fit. Plateau RMS is sine-equivalent of median RF peaks, not a spectral RMS. Stable window only; no startup verdict.')
    # Independent integration cross-check, using trapezoidal time weighting.
    integral=np.sum(np.diff(t)*(x[:-1]**2+x[1:]**2)/2)/(t[-1]-t[0])
    assert abs(np.sqrt(integral)*1e3-out['total_time_weighted_rms_mA'])<1e-9
    return out

def self_test():
    # Deliberately nonuniform sample density; DC and sinusoidal amplitude are known.
    t=np.linspace(0,1,20001)**1.5
    x=2*np.sin(2*np.pi*31*t)+.3
    rms=np.sqrt(weights(t)@(x*x)/sum(weights(t)))
    amp,err=fit(t,x,31)
    assert abs(rms-np.sqrt(2+.09))<1e-5
    assert abs(amp-np.sqrt(2))<1e-10 and err<1e-20

if __name__=='__main__':
    self_test()
    result=analyse(ROOT/'results/closure_sense10_preliminary.raw')
    (ROOT/'results/closure_sense10_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
