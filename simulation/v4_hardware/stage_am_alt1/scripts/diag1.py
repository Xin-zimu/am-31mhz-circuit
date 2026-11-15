# -*- coding: utf-8 -*-
"""Diagnose: what is the DC operating point of each modulator stage?"""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
from lib1 import ST
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.join(ST,"bench","mod_C_collector")
R=load_ngraw(os.path.join(B,"mod_C_collector.raw"))
print("vars:",[k for k in R if not k.startswith("v(")][:6], "...")
vs=[k for k in R if k.startswith("v(")]
print("nodes:",len(vs))
t=R["time"]
for k in ("v(m9src)","v(m9b)","v(m9rail)","v(m9base)","v(m9col)","v(m9emit)","v(amout)","v(out)","v(vcc)"):
    if k in R:
        v=R[k]
        print("%-12s mean=%+8.4f  min=%+8.4f  max=%+8.4f"%(k,v.mean(),v.min(),v.max()))
