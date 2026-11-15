# -*- coding: utf-8 -*-
"""Validate AD835_Behav.sub adapter reproduces the .asc exactly."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw, run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
d=os.path.join(STAGE,"bench"); os.makedirs(d,exist_ok=True)

TB = """V1 X1 0 PULSE(-1 1 0 1m 1m 0 2m)
V2 VPOS 0 5
V3 0 VNEG 5
V4 Y1 0 1
V5 Z 0 0
"""

p1=os.path.join(d,"val_adapter.net")
open(p1,"w",encoding="utf-8").write("* adapter validation\n"
    ".include ../adapted/AD835_Behav.sub\n" + TB +
    "XU X1 0 Y1 0 Z W VPOS VNEG AD835_BEHAV\n"
    ".options plotwinsize=0\n.tran 0 2m 0 50n\n.end\n")
r=run(p1); print("adapter rc",r.returncode)
if r.returncode: print(log(p1)[-1500:])

orig=open(os.path.join(STAGE,"ltspice_netlist","AD835_Behav_Model.net"),encoding="latin-1").read().splitlines()
flat=[l for l in orig if l.strip() and not l.strip().startswith(("*",".tran",".backanno",".end",".lib"))]
flat=[l for l in flat if l.split()[0] not in ("V1","V2","V3","V4","V5")]
p2=os.path.join(d,"val_flat.net")
open(p2,"w",encoding="utf-8").write("* flat reference\n"+"\n".join(flat)+"\n"+TB+
   ".lib C:\\Users\\86139\\AppData\\Local\\LTspice\\lib\\cmp\\standard.dio\n"
   ".options plotwinsize=0\n.tran 0 2m 0 50n\n.end\n")
r2=run(p2); print("flat rc",r2.returncode)
if r2.returncode: print(log(p2)[-1500:])

a=load_raw(os.path.join(d,"val_adapter.raw")); b=load_raw(os.path.join(d,"val_flat.raw"))
common=[k for k in ["V(W)","V(w)","V(Z)","V(X1)","V(Y1)","V(VNEG)"] if k in a and k in b]
print("\ncomparing:", common)
ok=True
for k in common:
    dd=np.max(np.abs(a[k]-b[k])); pk=np.max(np.abs(b[k]))
    rel = dd/pk if pk>0 else dd
    print("  %-8s maxdiff=%.3e  peak=%.6f  rel=%.2e" % (k,dd,pk,rel))
    if rel>1e-9: ok=False
print("\nADAPTER BIT-EXACT:", ok)
