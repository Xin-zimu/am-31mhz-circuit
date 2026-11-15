# -*- coding: utf-8 -*-
"""Module 6: project-specific AM simulation.
Builds an AD835 variant of the FROZEN netlist by replacing ONLY the POLY(3)
element with an AD835 instance. The frozen file itself is never modified.

Frozen relationship (final_actual.cir line 268):
  E1 7 8 POLY(3) (1,2) (3,4) (5,6) 0 0.6 0 0 0 0.1 0 0 0 0 ...
  -> TP3 = 0.6*V(TP2) + 0.1*V(TP2)*V(V1)  =  Vc*(0.6 + 0.1*Vm)

AD835 replacement (datasheet Fig.23 "A" topology):
  Y1=TP2, Y2=0, Z=TP2, X1=Xnode, X2=0, W=TP3
  W = X*Y/U + Z = Vc*(X/U + 1)
  With U=1.05:  X = 0.105*Vm - 0.42  ->  Vc*(0.6 + 0.1*Vm)   [exact match]
  With U=1.00 (what BOTH models actually use): Vc*(0.58 + 0.105*Vm)
"""
import os, sys, re, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod6"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")

BASE=open(NET,encoding="latin-1").read()
# strip any prior analysis card so we control it
BASE=re.sub(r"^\.tran.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)

XNET = """* ---- AD835 X-input network: X = 0.105*Vm - 0.42 (design values) ----
RXA V1 XA 100k
RXB XA VN5 125k
RXC XA 0 12.947k
VXBIAS VN5 0 -5
"""

def build(name, ad835_line, extra="", xnet=XNET, keep_poly=False):
    body = BASE
    if not keep_poly:
        body = re.sub(r"^xEAM_-EAM.*$", "* [replaced by AD835]", body, flags=re.M)
        body = re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS", "", body, flags=re.M|re.S)
    body += "\n" + xnet + extra + "\n" + ad835_line
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+"""
.options plotwinsize=0
.tran 0 350u 300u 0.5n
.end
""")
    return p

def ad835A(m, sub="AD835_BEHAV"):
    return ("* AD835 (A topology: Y1=TP2 Y2=0 Z=TP2 X1=XA X2=0 W=TP3)\n"
            "VADP ADP 0 5\nVADN ADN 0 -5\n"
            "XAD835 XA 0 TP2 0 ADN TP2 TP3 ADP %s\n" % sub)

# ---------- 1) POLY reference (frozen, untouched) ----------
p=build("ref_poly", "", xnet="", keep_poly=True)
R,lg,rc=run_and_load(p,ascii=True)
print("POLY ref rc",rc,"  nodes:",len([k for k in R]))
print("  TP3 min/max: %.4f / %.4f"%(np.min(R["V(tp3)"]),np.max(R["V(tp3)"])))
print("  V1  min/max: %.4f / %.4f"%(np.min(R["V(v1)"]),np.max(R["V(v1)"])))
print("  TP2 min/max: %.4f / %.4f"%(np.min(R["V(tp2)"]),np.max(R["V(tp2)"])))
np.savez(os.path.join(RES,"ref_poly.npz"),
         t=R["time"], tp3=R["V(tp3)"], v1=R["V(v1)"], tp2=R["V(tp2)"])
json.dump({"tmax":float(R["time"][-1]),"n":int(len(R["time"]))},open(os.path.join(RES,"ref_poly_meta.json"),"w"))

# ---------- 2) AD835 model A ----------
p=build("ad835_A", ad835A("A",".include ../../models/third_party_GLuisF/ad835.sub\nXPLACE XA 0 TP2 0 ADN TP2 TP3 ADP AD835\n"))
print("\nbuilt", p)
