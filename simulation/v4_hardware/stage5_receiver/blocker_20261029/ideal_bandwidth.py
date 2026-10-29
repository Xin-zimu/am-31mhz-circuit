"""Ideal complex-envelope LTI reference, not an LC acceptance test."""
import numpy as np,json
from scipy.signal import correlate,correlation_lags
from run_diagnosis import HERE,wave_metrics,fixed

rows=[];waves={};dt=2e-9;period=50e-6;n=25000
t=np.arange(4*n)*dt;f=np.fft.fftfreq(len(t),dt)
for duty in [.1,.5]:
    phase=np.mod(t,period);w=duty*period-50e-9
    mod=np.full(len(t),-1.)
    mod[phase<50e-9]=-1+2*phase[phase<50e-9]/50e-9
    mod[(phase>=50e-9)&(phase<50e-9+w)]=1
    ix=(phase>=50e-9+w)&(phase<100e-9+w)
    mod[ix]=1-2*(phase[ix]-50e-9-w)/50e-9
    env=1+.5*mod
    for bw in [7.32e6,2e6,1e6]:
        # Equivalent narrowband 2-resonator (4th order RF) ideal Butterworth.
        s=1j*f/(bw/2);h=1/(s*s+np.sqrt(2)*s+1)
        y=np.fft.ifft(np.fft.fft(env)*h).real
        u=t[n:3*n];v=y[n:3*n]
        m=wave_metrics(u,v)
        h20=1/(1-(20e3/(bw/2))**2+1j*np.sqrt(2)*20e3/(bw/2))
        rows.append(dict(bw_hz=bw,duty=duty,**m,sideband20k_db=float(20*np.log10(abs(h20))),
            rejection_at_2MHz_db=float(-10*np.log10(1+(2e6/(bw/2))**4)),
            center_loss_db=0,evidence_type='ideal complex-envelope frequency-domain calculation'))
        waves[f'{bw:g}_{duty}']=y[n:2*n]
fixed(HERE/'ideal_bandwidth.json',json.dumps(rows,indent=2).encode())
np.savez(HERE/'ideal_waveforms.npz',time=t[:n],**waves)
for r in rows:print(json.dumps(r))
