# -*- coding: utf-8 -*-
import os, sys, re, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod6"); os.makedirs(B,exist_ok=True)
BASE=open(NET,encoding="latin-1").read()
BASE=re.sub(r"^\.tran.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)
p=os.path.join(B,"ref_poly.net")
open(p,"w",encoding="utf-8").write(BASE+"""
.options plotwinsize=0
.tran 0 400u 300u 2n uic
.end
""")
R,lg,rc=run_and_load(p,ascii=True,expect_ok=False)
print("rc",rc)
if R is None:
    print(lg[-2500:])
else:
    t=R["time"]
    print("t range %.4g .. %.4g  n=%d"%(t[0],t[-1],len(t)))
    for k in ("V(tp3)","V(v1)","V(tp2)","V(tp4)"):
        if k in R:
            v=R[k]; print("  %-8s min=%+9.4f max=%+9.4f"%(k, v.min(), v.max()))
