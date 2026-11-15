# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
from lib1 import ST
sys.stdout.reconfigure(encoding="utf-8")
print(open(os.path.join(ST,"bench","E_470_100","E_470_100.cir"),encoding="latin-1").read()[-1100:])
R=load_ngraw(os.path.join(ST,"bench","E_470_100","E_470_100.raw"))
for k in ("v(m9src)","v(m9b)","v(m9rail)","v(m9base)","v(m9emit)","v(m9col)","v(amout)","v(m9fe)"):
    if k in R:
        v=R[k]; print("%-10s mean=%+7.4f min=%+7.4f max=%+7.4f"%(k,v.mean(),v.min(),v.max()))
