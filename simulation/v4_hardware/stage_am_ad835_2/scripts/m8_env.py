# -*- coding: utf-8 -*-
"""Module 8: analyse project waveforms - envelope, AM depth, FFT, vs POLY."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod6"); RES=os.path.join(STAGE,"results")

def envelope(t, v, f_car=31e6, ncyc=64):
    """Peak envelope: max/min per integer number of carrier cycles."""
    T=ncyc/f_car
    n=int((t[-1]-t[0])/T)
    hi=np.empty(n); lo=np.empty(n); tc=np.empty(n)
    for i in range(n):
        a=t[0]+i*T; b=a+T
        m=(t>=a)&(t<b)
        if m.sum()<2: hi[i]=np.nan; lo[i]=np.nan; continue
        hi[i]=v[m].max(); lo[i]=v[m].min(); tc[i]=0.5*(a+b)
    return tc, hi, lo

def analyse(tag, t, w, v1, tmax=None):
    if tmax is not None:
        m=t>=t[0]+(t[-1]-t[0])*0.5
        t,w,v1=t[m],w[m],v1[m]
    tc,hi,lo=envelope(t,w)
    ok=~np.isnan(hi)
    tc,hi,lo=tc[ok],hi[ok],lo[ok]
    # sample at v1 high and low plateaus
    vh=np.interp(tc,t,v1)
    hiP=np.percentile(hi,95); loP=np.percentile(lo,5)
    # plateau separation via histogram of (hi-lo)
    return {"tc":tc,"hi":hi,"lo":lo,"vh":vh,
            "hiP":float(hiP),"loP":float(loP)}

def fft_am(t,w,f_car=31e6,f_mod=20e3):
    m=t>=t[0]+(t[-1]-t[0])*0.5
    tt=t[m]; ww=w[m]
    tt=tt-tt[0]
    # resample uniform
    n=2**18
    fs=n/(tt[-1])
    tu=np.arange(n)/fs
    wu=np.interp(tu,tt,ww)
    win=np.hanning(n)
    S=np.abs(np.fft.rfft(wu*win))*2/np.sum(win)
    f=np.fft.rfftfreq(n,1/fs)
    return f,S

def peak_near(f,S,f0,span):
    m=(f>f0-span)&(f<f0+span)
    if not m.any(): return 0.0
    return float(S[m].max())

out={}
for tag in ("ref_poly","adA_U105","adA_U100","adB_U105","adB_U100"):
    p=os.path.join(B,tag+".raw")
    if not os.path.exists(p) or os.path.getsize(p)==0: 
        print("%-10s : no raw"%tag); continue
    R=load_raw(p)
    t=R["time"]; w=R["V(tp3)"]; v1=R["V(v1)"]
    A=analyse(tag,t,w,v1)
    f,S=fft_am(t,w)
    c=peak_near(f,S,31e6,3e5)
    sb=f0=31e6
    lsb=peak_near(f,S,31e6-20e3,6e3); usb=peak_near(f,S,31e6+20e3,6e3)
    dc=peak_near(f,S,0,5e3)
    out[tag]={"hiP":A["hiP"],"loP":A["loP"],"vpp":A["hiP"]-A["loP"],
              "carrier":c,"lsb":lsb,"usb":usb,"dc":dc}
    print("%-10s envelope hi=%+7.4f lo=%+7.4f  Vpp=%6.4f | FFT: DC=%7.4f  fc=%7.4f  LSB=%7.5f USB=%7.5f"%(
        tag,A["hiP"],A["loP"],A["hiP"]-A["loP"],dc,c,lsb,usb))
json.dump(out,open(os.path.join(RES,"m8_env.json"),"w"),indent=1)
