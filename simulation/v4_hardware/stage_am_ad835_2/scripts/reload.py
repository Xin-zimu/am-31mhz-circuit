# -*- coding: utf-8 -*-
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","fin"); RES=os.path.join(STAGE,"results")
store={}
for tag in ("ref_poly","A_510_680","A_direct","A_U100","B_short"):
    p=os.path.join(B,tag+".raw")
    if os.path.exists(p) and os.path.getsize(p)>0:
        try:
            store[tag]=load_raw(p)
            t=store[tag]["time"]
            print("%-11s t=%.1f..%.1f us  n=%d"%(tag,t[0]*1e6,t[-1]*1e6,len(t)))
        except Exception as e:
            print(tag,"ERR",e)
np.savez(os.path.join(RES,"fin.npz"), **{f"{a}__{b}":v for a,d in store.items() for b,v in d.items()})
print("saved")
