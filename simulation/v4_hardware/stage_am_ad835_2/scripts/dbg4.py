# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
d=os.path.join(STAGE,"bench")
for tag in ("val_adapter","val_flat"):
    r=load_raw(os.path.join(d,tag+".raw"))
    t=r["time"]; w=r["V(w)"]
    print("==",tag,"n=",len(t),"tmax=%.4g"%t[-1])
    print("   V(w): min=%.4g max=%.4g mean=%.4g  last=%.6g"%(w.min(),w.max(),w.mean(),w[-1]))
    print("   V(w) at t=0.5ms:", np.interp(0.5e-3,t,w), " at 1.0ms:", np.interp(1.0e-3,t,w), " at 1.9ms:", np.interp(1.9e-3,t,w))
    if "V(11)" in r: print("   V(11) min/max", r["V(11)"].min(), r["V(11)"].max())
