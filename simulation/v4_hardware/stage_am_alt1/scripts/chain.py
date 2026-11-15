# -*- coding: utf-8 -*-
"""Measure the chain: how much 31 MHz gain is actually available, node by node."""
import os, sys, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
from lib1 import ST
B=os.path.join(ST,"bench","F_100_22_470_2200")
R=load_ngraw(os.path.join(B,"F_100_22_470_2200.raw"))
t=R["time"]
def cpp(v):
    T=32/31e6; n=int((t[-1]-t[0])/T); a=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: a.append(v[m].max()-v[m].min())
    return np.percentile(a,97), np.percentile(a,3)
print("node          dc         carrier hi/lo Vpp")
for k in ("v(out)","v(fen)","v(at1)","v(xbn)","v(ven)","v(vm1)","v(xcn)","v(amout)"):
    if k in R:
        hi,lo=cpp(R[k]); v=R[k]
        print("%-11s %+8.4f   hi=%8.5f lo=%8.5f"%("v("+k[2:]+")" if False else k,v.mean(),hi,lo))
print()
print("chain gain: out -> amout = %.5f / %.5f = %.2f"%(
    cpp(R["v(amout)"])[0], cpp(R["v(out)"])[0],
    cpp(R["v(amout)"])[0]/cpp(R["v(out)"])[0]))
print("needed for POLY-equivalent 2.015 Vpp at VH: 2.015/%.5f = %.0f x"%(
    cpp(R["v(amout)"])[0], 2.015/cpp(R["v(amout)"])[0]))
