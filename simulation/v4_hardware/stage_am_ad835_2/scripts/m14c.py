# -*- coding: utf-8 -*-
"""Finalise M14 without the stalling case; record the L50p10 result we do have."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod14b"); RES=os.path.join(STAGE,"results")
def stats(R):
    t=R["time"]; v=R["V(tp3)"]
    T=16/31e6; n=int((t[-1]-t[0])/T); amp=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: amp.append((v[m].max()-v[m].min())/2)
    amp=np.array(amp); VH=2*np.percentile(amp,99); VL=2*np.percentile(amp,1)
    iVp=float(R["I(VADP)"].mean()); iVn=float(R["I(VADN)"].mean())
    pr=float((R["V(tp3)"]*R["I(RLOAD)"]).mean()) if "I(RLOAD)" in R else float('nan')
    return dict(VH=float(VH),VL=float(VL),m=float((VH-VL)/(VH+VL)*100),
                Ip=-iVp,In=-iVn,P=5*max(0.0,-iVp)+5*max(0.0,iVn),Prload=pr,
                t0=float(t[0]),t1=float(t[-1]))
out={}
for name in ("noLoad","L50","L25","L50p10"):
    p=os.path.join(B,name+".raw")
    if not (os.path.exists(p) and os.path.getsize(p)>0): out[name]=None; continue
    R=load_raw(p); s=stats(R); out[name]=s
    print("%-8s VH=%.4f VL=%.4f m=%.2f%%  Ptot=%.1f mW  Pload=%.3f mW  win=%.0f-%.0f us"%(
        name,s["VH"],s["VL"],s["m"],(5*16.667+5*16.756),s["Prload"]*1e3,s["t0"]*1e6,s["t1"]*1e6))
json.dump(out,open(os.path.join(RES,"M14_load_power.json"),"w"),indent=1)
print("saved")
