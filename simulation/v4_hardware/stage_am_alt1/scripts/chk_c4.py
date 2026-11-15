# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ngraw import load_ngraw
sys.stdout.reconfigure(encoding="utf-8")
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R=load_ngraw(os.path.join(ST,"bench","ng","c4.raw"))
print("vars:",list(R.keys()))
t=R["time"]; v=R["v(out)"]
print("t: %.5g .. %.5g  n=%d"%(t[0],t[-1],len(t)))
T=200/31e6; m=t>=t[-1]-T
print("frozen C4 @ 2k||10p -> TP2 = %.4f Vpp  (%.4f .. %.4f)"%(
    v[m].max()-v[m].min(), v[m].min(), v[m].max()))
# also THD of the carrier
tt=t[m]-t[m][0]; fs=len(tt)/(tt[-1])
from numpy.fft import rfft, rfftfreq
w=np.hanning(len(v[m])); S=np.abs(rfft(v[m]*w)); f=rfftfreq(len(v[m]),1/fs)
k=np.argmax(S)
f0=f[k]
def band(f0,w_): 
    ms=(f>f0-w_)&(f<f0+w_); return S[ms].max()
fund=band(f0,3e5)
hs=[band(2*f0,6e5),band(3*f0,9e5)]
print("carrier f0 = %.4f MHz ; H2/fund=%.1f dB ; H3/fund=%.1f dB"%(
    f0/1e6,20*np.log10(hs[0]/fund),20*np.log10(hs[1]/fund)))
print("THD(2,3) = %.2f%%"%(np.sqrt(hs[0]**2+hs[1]**2)/fund*100))
