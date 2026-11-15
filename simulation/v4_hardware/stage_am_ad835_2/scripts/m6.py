# -*- coding: utf-8 -*-
"""Module 6: project AM simulation - frozen POLY vs AD835 (both models)."""
import os, sys, re, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod6"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")
BASE=open(NET,encoding="latin-1").read()
BASE=re.sub(r"^\.tran.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)

def xnet(u=1.05):
    """X = 0.105*Vm - 0.42 for U=1.05 ; X = 0.1*Vm - 0.4 for U=1.0"""
    a = 0.1*u          # slope
    b = 0.4*u          # offset magnitude
    # solve Thevenin divider from Vm through R1, from -5 through R2, R3 to gnd
    # node must satisfy: Vx = a*Vm - b with zero input current
    # choose R1=100k => Thevenin R = 100k||... ; use 3-resistor exact solve
    R1 = 100e3
    # unknowns R2 (to -5), R3 (to gnd).  Conductances:
    # (Vm-Vx)/R1 + (-5-Vx)/R2 + (0-Vx)/R3 = 0  for all Vm
    # => coefficient of Vm: 1/R1 = a*(1/R1+1/R2+1/R3) ... solve numerically
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p
        G=1/R1+1/R2+1/R3
        return [1/R1 - a*G, (-5/R2) - (-b)*G]
    R2,R3=fsolve(eqs,[125e3,13e3],full_output=False)
    return ("* X network for U=%.3f : X = %.4f*Vm - %.4f\n"
            "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(u,a,b,R1,R2,R3))

def build(name, body_extra, analysis=".tran 0 400u 300u 2n uic"):
    body=BASE
    body=re.sub(r"^xEAM_-EAM.*$","* [POLY removed - AD835 variant]",body,flags=re.M)
    body=re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS", "", body, flags=re.M|re.S)
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+"\n"+body_extra+"\n.options plotwinsize=0\n"+analysis+"\n.end\n")
    return p

SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
def adA(): return SUP+"XAD835 XA 0 TP2 0 ADN TP2 TP3 ADP AD835\n"
def adB(): return SUP+"XAD835 XA 0 TP2 0 ADN TP2 TP3 ADP AD835_BEHAV\n"
INCA=".include ../../models/third_party_GLuisF/ad835.sub\n"
INCB=".include ../../adapted/AD835_Behav.sub\n"

jobs=[("ref_poly", "", "", True),
      ("adA_U105", xnet(1.05), INCA+adA(), False),
      ("adB_U105", xnet(1.05), INCB+adB(), False),
      ("adA_U100", xnet(1.00), INCA+adA(), False),
      ("adB_U100", xnet(1.00), INCB+adB(), False)]

store={}
for name,xn,extra,poly in jobs:
    if poly:
        body=BASE+"\n"
        p=os.path.join(B,name+".net")
        open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n.tran 0 400u 300u 2n uic\n.end\n")
    else:
        p=build(name, xn+extra)
    R,lg,rc=run_and_load(p,ascii=True,expect_ok=False)
    if R is None:
        print("FAIL",name); print(lg[-900:]); continue
    t=R["time"]; tp3=R["V(tp3)"]; v1=R["V(v1)"]; tp2=R["V(tp2)"]
    keep={"t":t,"tp3":tp3,"v1":v1,"tp2":tp2}
    for k in ("V(adp)","V(adn)","I(VADP)","I(VADN)","V(xa)","I(VXBIAS)"):
        if k in R: keep[k]=R[k]
    store[name]=keep
    print("%-10s rc=%d  n=%d  t=[%.4g,%.4g]  TP3=[%+.4f,%+.4f]  Vm=[%.4f,%.4f]  TP2=[%+.4f,%+.4f]"%(
        name,rc,len(t),t[0],t[-1],tp3.min(),tp3.max(),v1.min(),v1.max(),tp2.min(),tp2.max()))
    if "I(VADP)" in R:
        ip=-R["I(VADP)"]; iN=-R["I(VADN)"]
        print("           AD835 supply: I+=%.3f mA  I-=%.3f mA  P=%.2f mW (avg over saved window)"%(
            ip.mean()*1e3, iN.mean()*1e3, (5*ip.mean()+5*iN.mean())*1e3))

np.savez(os.path.join(RES,"m6_waveforms.npz"), **{f"{k}__{kk}":vv for k,v in store.items() for kk,vv in v.items()})
json.dump({k:{"n":int(len(v["t"])),"tmax":float(v["t"][-1])} for k,v in store.items()},
          open(os.path.join(RES,"m6_meta.json"),"w"), indent=1)
print("\nsaved m6_waveforms.npz")
