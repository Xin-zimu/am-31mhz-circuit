# -*- coding: utf-8 -*-
"""Module 13 (corrected): AM envelope = high/low carrier levels per modulation
half-cycle, following the definition used in stage AM-AD835.1:
   VH = 2*max(hi), VL = 2*min(hi),  m = (VH-VL)/(VH+VL)
"""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
RES=os.path.join(STAGE,"results")
Z=np.load(os.path.join(RES,"fin.npz"))
def arr(t,k):
    kk="%s__%s"%(t,k); return Z[kk] if kk in Z else None
tags=[t for t in ("ref_poly","A_510_680","A_direct","A_U100","B_short") if arr(t,"time") is not None]
FC=31e6; FM=20e3

def env(t,v,ncyc=16):
    T=ncyc/FC; n=int((t[-1]-t[0])/T); hi=[];lo=[];tc=[]
    for i in range(n):
        a=t[0]+i*T; b=a+T; m=(t>=a)&(t<b)
        if m.sum()<3: continue
        hi.append(v[m].max()); lo.append(v[m].min()); tc.append(0.5*(a+b))
    return np.array(tc),np.array(hi),np.array(lo)
def spec(t,v,n=2**17):
    tt=t-t[0]; fs=n/(tt[-1]); tu=np.arange(n)/fs
    vu=np.interp(tu,tt,v); w=np.hanning(n)
    S=np.abs(np.fft.rfft(vu*w))*2/np.sum(w)
    return np.fft.rfftfreq(n,1/fs),S
def pk(f,S,f0,span):
    m=(f>f0-span)&(f<f0+span); return float(S[m].max()) if m.any() else 0.0

out={}
print("%-11s %8s %8s %8s %8s %7s %7s"%("case","VH(Vpp)","VL(Vpp)","m%","fc","THD%","car.feed"))
for tag in tags:
    t=arr(tag,"time"); v=arr(tag,"V(tp3)"); vm=arr(tag,"V(v1)")
    tc,hi,lo=env(t,v)
    amp=(hi-lo)/2.0
    VH=2*np.percentile(amp,99); VL=2*np.percentile(amp,1)
    m=(VH-VL)/(VH+VL)*100
    f,S=spec(t,v)
    fc=pk(f,S,FC,2e5)
    lsb=pk(f,S,FC-FM,8e3); usb=pk(f,S,FC+FM,8e3)
    hs=[pk(f,S,k*FC,2e5) for k in (2,3,4,5)]
    thd=np.sqrt(sum(h*h for h in hs))/fc*100 if fc>0 else float('nan')
    # carrier feedthrough = residual at fc when X=0 would be; here report DC and the
    # lowest envelope level relative to the highest (carrier suppression floor)
    out[tag]=dict(VH=float(VH),VL=float(VL),m=float(m),fc=float(fc),
                  lsb_dBc=float(20*np.log10(lsb/fc)) if fc>0 and lsb>0 else None,
                  usb_dBc=float(20*np.log10(usb/fc)) if fc>0 and usb>0 else None,
                  thd=float(thd), dc=float(pk(f,S,0,8e3)),
                  vm_lo=float(np.percentile(vm,1)), vm_hi=float(np.percentile(vm,99)),
                  t0=float(t[0]),t1=float(t[-1]))
    o=out[tag]
    print("%-11s %8.4f %8.4f %8.3f %8.4f %7.3f  LSB=%6.1f dBc USB=%6.1f dBc"%(
        tag,VH,VL,m,fc,thd,o["lsb_dBc"] or 0,o["usb_dBc"] or 0))

ref=out["ref_poly"]
print("\nReference POLY: VH=%.4f VL=%.4f m=%.3f%%  (stage AM-AD835.1 predicted VH=2.01496 VL=1.21496 m=24.768%%)"%(
    ref["VH"],ref["VL"],ref["m"]))
print("\nDeviations vs frozen POLY:")
for tag in tags:
    if tag=="ref_poly": continue
    o=out[tag]
    print("  %-10s VH %+7.2f%%  VL %+7.2f%%  m %+6.2f pp  THD %+6.2f pp"%(
        tag,(o["VH"]/ref["VH"]-1)*100,(o["VL"]/ref["VL"]-1)*100,o["m"]-ref["m"],o["thd"]-ref["thd"]))
json.dump(out,open(os.path.join(RES,"M13_env.json"),"w"),indent=1)
print("saved M13_env.json")
