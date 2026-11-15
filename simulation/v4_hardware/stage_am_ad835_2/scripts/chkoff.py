# -*- coding: utf-8 -*-
import os, sys, re
sys.stdout.reconfigure(encoding="utf-8")
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\bench\fin\ref_poly.raw"
raw=open(p,'rb').read()
i=raw.find(b"Values:")
print(repr(raw[i:i+300]))
print("---- tmax check via python parse ----")
import numpy as np
sys.path.insert(0,r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\scripts")
from ltraw import load_raw
R=load_raw(p)
t=R["time"]
print("t[0], t[-1], n =", t[0], t[-1], len(t))
print("dt min/max:", np.diff(t).min(), np.diff(t).max())
