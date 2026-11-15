# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
from lib1 import ST
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.join(ST,"bench","C_final")
R=load_ngraw(os.path.join(B,"C_final.raw"))
t=R["time"]
def pp(v):
    T=32/31e6; n=int((t[-1]-t[0])/T); a=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: a.append(v[m].max()-v[m].min())
    return np.percentile(a,97), np.percentile(a,3)
print("node           mean      carrier hi/lo Vpp")
for k in ("v(out)","v(m9fe)","v(m9at)","v(m9base)","v(m9emit)","v(m9col)","v(m9rail)","v(amout)"):
    if k in R:
        hi,lo=pp(R[k]); v=R[k]
        print("%-11s %+8.4f   hi=%7.4f lo=%7.4f   dc_range %.3f..%.3f"%(k,v.mean(),hi,lo,v.min(),v.max()))
