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
    print("==",tag,"n=",len(t))
    print("   time[0:4]=", t[:4], " time[-3:]=", t[-3:])
    print("   V(w)[0:4]=", w[:4])
    print("   V(w)[-308:][:4]=", w[-308:-304])
    order=np.argsort(t)
    ts=t[order]; ws=w[order]
    print("   sorted t range %.4g .. %.4g"%(ts[0],ts[-1]))
    for probe in (1e-4,5e-4,1e-3,1.5e-3,1.9e-3):
        print("      t=%.1e -> w=%.6g"%(probe, np.interp(probe,ts,ws)))
