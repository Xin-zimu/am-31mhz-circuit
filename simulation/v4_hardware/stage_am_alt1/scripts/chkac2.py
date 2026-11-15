# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1"
p=os.path.join(ST,"bench","ac3","c_78_1000_10.raw")
hdr=open(p,encoding="latin-1").read().split("Values:")[0]
print(hdr)
R=load_ngraw(p)
for k,v in R.items():
    print(k, "n=",len(v), "first=",v[0])
