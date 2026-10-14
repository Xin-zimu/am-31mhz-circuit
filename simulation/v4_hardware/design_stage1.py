from pathlib import Path
import json,sys
import numpy as np
from scipy.optimize import brentq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_simulation import run_spice, read_raw
HERE=Path(__file__).resolve().parent
DB=json.loads((HERE/'models/Multisim_LM393.json').read_text())
MODEL=next(m['DATA'] for m in DB['models'] if m['MODEL_ID']=='LM393/TI')
# Only the subcircuit identifier changes to an ASCII identifier; no model parameters change.
MODEL=MODEL.replace('LM393/TI','LM393_TI')
(HERE/'models/LM393_TI.lib').write_text(MODEL,encoding='ascii')

def circuit(rfreq=33000, dp=.4, ap=.9, supply=5, load=1e6):
    return f'''LM393P Stage 1 - RC oscillator, PWM threshold, amplitude potentiometer
* TI LM393 macromodel from installed NI Multisim master database LM393/TI.
* U1A: DIP pins IN+=3 IN-=2 V+=8 GND=4 OUT=1
* U1B: DIP pins IN+=5 IN-=6 V+=8 GND=4 OUT=7
V5 V5 0 {supply}
CDEC V5 0 100n
CBULK V5 0 10u
RPU1 V5 OSC 2.2k
RHT V5 HYST 30k
RHB HYST 0 10k
RHF OSC HYST 20k
RFIX OSC FSET 22k
RVRF FSET RAMP {rfreq-22000:.10g}
CT RAMP 0 1n
XU1A HYST RAMP V5 0 OSC LM393_TI
* VDUTY resistor chain: 10k + 10k potentiometer + 4.7k.
RDT V5 DUTY_TOP 10k
RVDT DUTY_TOP DUTY {10000*(1-dp):.10g}
RVDB DUTY DUTY_BOT {10000*dp:.10g}
RDB DUTY_BOT 0 4.7k
XU1B DUTY RAMP V5 0 PWM_RAW LM393_TI
RPU2 V5 PWM_RAW 2.2k
* 20k amplitude potentiometer, wiper at V1, includes specified load.
RVAT PWM_RAW V1 {max(.01,20000*(1-ap)):.10g}
RVAB V1 0 {max(.01,20000*ap):.10g}
RINPUT V1 0 {load:.10g}
CINPUT V1 0 15p
{MODEL}
.options plotwinsize=0 reltol=0.0001
.save V(RAMP) V(HYST) V(OSC) V(DUTY) V(PWM_RAW) V(V1)
.tran 50n 1.5m 0 50n
.end
'''

def metrics(d):
    t=d['time']; mask=t>.8e-3
    # Uniform resampling avoids adaptive time-step bias in percentiles.
    tt=np.arange(.8e-3,1.5e-3,20e-9)
    y=np.interp(tt,t,d['v(v1)']); lo,hi=np.quantile(y,[.02,.98]); mid=(lo+hi)/2
    yy=d['v(v1)']; cross=[]
    for up in [True,False]:
        ii=np.where(((yy[:-1]<mid)&(yy[1:]>=mid) if up else (yy[:-1]>=mid)&(yy[1:]<mid)) & (t[:-1]>.8e-3))[0]
        cross.append(t[ii]+(mid-yy[ii])/(yy[ii+1]-yy[ii])*(t[ii+1]-t[ii]))
    up,dn=cross
    period=np.mean(np.diff(up))
    widths=[dn[dn>x][0]-x for x in up if np.any(dn>x)]
    return dict(frequency_hz=1/period,duty_pct=np.mean(widths)/period*100,vpp=hi-lo,low_v=lo,high_v=hi,
                ramp_min=float(d['v(ramp)'][mask].min()),ramp_max=float(d['v(ramp)'][mask].max()))

def evaluate(rfreq,dp,ap,name='trial',supply=5,load=1e6):
    p=HERE/(name+'.cir');p.write_text(circuit(rfreq,dp,ap,supply,load),encoding='ascii')
    run_spice(p);return metrics(read_raw(p.with_suffix('.raw')))

if __name__=='__main__':
    rfreq=brentq(lambda r:evaluate(r,.2,.9)['frequency_hz']-20000,33000,45000,xtol=.01)
    print('RFREQ',rfreq,flush=True)
    records=[]
    for duty in [10,20,30,40,50]:
        dp=brentq(lambda p:evaluate(rfreq,p,.9)['duty_pct']-duty,.001,.4,xtol=1e-7)
        for amp in [1,2,3,4]:
            ap=brentq(lambda p:evaluate(rfreq,dp,p)['vpp']-amp,.1,.99,xtol=1e-7)
            name=f'LM393_20k_D{duty}_A{amp}'
            m=evaluate(rfreq,dp,ap,name)
            records.append(dict(name=name,rfreq=rfreq,dp=dp,ap=ap,target_duty=duty,target_amp=amp,**m))
            print(name,m,flush=True)
    (HERE/'calibration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
