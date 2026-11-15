# -*- coding: utf-8 -*-
"""Isolate the model-B output-stage pathology."""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","iso"); os.makedirs(B,exist_ok=True)

def T(name, body, analysis=".tran 0 20u 0 1n", to=60):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write("* iso\n"+body+"\n.options plotwinsize=0\n"+analysis+"\n.end\n")
    t0=time.time()
    try:
        r=run(p,ascii=True,timeout=to)
    except Exception as e:
        print("%-22s TIMEOUT"%name); return None
    dt=time.time()-t0
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    print("%-22s rc=%d %5.1fs raw=%d"%(name,r.returncode,dt,sz))
    if r.returncode: print("   ", [l for l in log(p).splitlines() if "ERROR" in l or "Fail" in l][:3])
    return load_raw(os.path.join(B,name+".raw")) if sz else None

SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
# 1) only the limit block, driven by an ideal source (no multiplier)
print("--- output limiter alone, W driven by ideal source through 10 ohm ---")
for tag,vw in (("lim_lo","0.5"),("lim_hi","2.4"),("lim_vhi","3.0")):
    R=T(tag, SUP+"""
VDRV D 0 %s
R5 D W 10
B2 W 0 I=table((V(W)-V(11)),-75m/1E4,-75m,75m/1E4,75m)
C7 11 0 {20m/1E9}
B5 11 0 I=Table((V(11)-V(W)),-10m,-20m,10m,20m)
R13 W 0 {2.5/75m}
"""%vw)
    if R is not None:
        print("     V(W) settles to %.4f V"%(R["V(w)"][-1]))

print("\n--- full model B subckt, static X/Y/Z, DC-ish ---")
R=T("b_static", ".include ../../adapted/AD835_Behav.sub\n"+SUP+
    "VX1 X1 0 0.5\nVX2 X2 0 0\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\n"
    "XU X1 X2 Y1 Y2 ADN Z W ADP AD835_BEHAV\nRL W 0 150\n","""
.tran 0 5u 0 0.5n""")
if R is not None:
    print("     V(W) final=%.4f  (expect 0.5*1/1.05+... ~0.476)"%R["V(w)"][-1])
