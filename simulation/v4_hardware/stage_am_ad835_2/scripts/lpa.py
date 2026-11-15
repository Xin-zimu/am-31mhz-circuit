# -*- coding: utf-8 -*-
"""Analyse the working 50 ohm || 10 pF case."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod14b"); RES=os.path.join(STAGE,"results")
R=load_raw(os.path.join(B,"LP_a.raw"))
t=R["time"]; v=R["V(tp3)"]; vm=R["V(v1)"]
print("window %.1f .. %.1f us  n=%d"%(t[0]*1e6,t[-1]*1e6,len(t)))
T=16/31e6; n=int((t[-1]-t[0])/T); amp=[];tc=[]
for i in range(n):
    m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
    if m.sum()>3: amp.append((v[m].max()-v[m].min())/2); tc.append(t[0]+(i+.5)*T)
amp=np.array(amp)*2; tc=np.array(tc)
print("envelope Vpp: min=%.4f max=%.4f"%(np.percentile(amp,1),np.percentile(amp,99)))
VH=np.percentile(amp,99); VL=np.percentile(amp,1)
print("VH=%.4f VL=%.4f m=%.2f%%"%(VH,VL,(VH-VL)/(VH+VL)*100))
pr=float((v*R["I(RLOAD)"]).mean())
print("Pload=%.3f mW  (50 ohm)"%(pr*1e3))
# compare to no-capacitor 50 ohm result
print("\nno-cap case: VH=0.9877 VL=0.5898  -> 10 pF changes VH by %+.3f%%"%((VH/0.9877-1)*100))
json.dump({"VH":float(VH),"VL":float(VL),"m":float((VH-VL)/(VH+VL)*100),"Pload":pr,
           "t0":float(t[0]),"t1":float(t[-1])},
          open(os.path.join(RES,"M14_L50p10.json"),"w"),indent=1)
