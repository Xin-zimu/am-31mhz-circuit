# -*- coding: utf-8 -*-
"""Diagnose the EF+CE collector modulator chain node by node."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
from lib1 import ST
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.join(ST,"bench","C_ef")
R=load_ngraw(os.path.join(B,"C_ef.raw"))
for k in ("v(out)","v(m9fb)","v(m9fe)","v(m9base)","v(m9emit)","v(m9col)","v(m9rail)","v(amout)"):
    if k in R:
        v=R[k]
        print("%-11s mean=%+7.4f  min=%+7.4f  max=%+7.4f  pp=%7.4f"%(k,v.mean(),v.min(),v.max(),v.max()-v.min()))
# carrier amplitude along the chain: per-window pp on each node
def pp(v,t):
    T=32/31e6; n=int((t[-1]-t[0])/T)
    a=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: a.append(v[m].max()-v[m].min())
    return np.percentile(a,97), np.percentile(a,3)
t=R["time"]
for k in ("v(out)","v(m9fe)","v(m9base)","v(m9col)","v(amout)"):
    hi,lo=pp(R[k],t); print("  %-11s carrier Vpp: hi=%.4f lo=%.4f"%(k,hi,lo))
