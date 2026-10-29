"""Separate RF envelope fidelity from detector nonlinearity; raw arrays are read-only."""
from run_diagnosis import *
import scipy.signal as sig

def rf_envelope(d,node):
    start=100e-6;n=3100;t=start+np.arange(n*64)/31e6/64
    v=np.interp(t,d['time'],d[f'v({node})']).reshape(n,64)
    e=2*np.abs(v@np.exp(-2j*np.pi*np.arange(64)/64)/64)
    te=start+(np.arange(n)+.5)/31e6
    return te,e

def main():
    rows=[]
    for v in ['R2','B_E1','A2M_r1M','A1M_r1M']:
        for duty in [10,50]:
            d=readraw(WORK/f'{v}_square{duty}.raw')
            for node in ['port','rf']:
                t,e=rf_envelope(d,node);m=wave_metrics(t,e)
                # Plateau reference comes from late in high and low intervals,
                # not 98th-percentile values that include ringing at narrow BW.
                phase=np.mod(t,50e-6);end=duty/100*50e-6
                low=float(np.median(e[(phase>35e-6)&(phase<45e-6)]))
                high=float(np.median(e[(phase>end-1.5e-6)&(phase<end-.5e-6)]))
                span=high-low
                m.update(plateau_low=low,plateau_high=high,
                    overshoot_plateau_pct=float((max(e)-high)/span*100),
                    undershoot_plateau_pct=float((low-min(e))/span*100))
                rows.append(dict(variant=v,duty_pct_input=duty,node=node,**m))
    fixed(HERE/'rf_envelope_metrics.json',json.dumps(rows,indent=2).encode())
    for r in rows:
        if r['node']=='port':print(json.dumps(r))

if __name__=='__main__':main()
