# -*- coding: utf-8 -*-
"""ALT-1 step 2 (fixed): POLY(3) ideal reference + C4 output impedance."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, pk, carrier_thd, ST
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.join(ST,"bench","ref"); os.makedirs(B,exist_ok=True)
VM_LO=0.0748175; VM_HI=4.0748175
# POLY(3) coefficient order (SPICE3): P0, P1(V1), P2(V2), P3(V3),
#   P4(V1^2), P5(V1V2), P6(V1V3), P7(V2^2), P8(V2V3), P9(V3^2)
# Project: W = 0.6*V1 + 0.1*V1*V2  ->  P1=0.6, P5=0.1, rest 0
net="""* POLY(3) ideal reference, project spec, 50 ohm || 10 pF
VC tp2 0 sin(0 1 31e6)
VM mod 0 pulse(%g %g 10u 20n 20n 4.98u 50u)
EAM tp3 0 POLY(3) (tp2,0) (mod,0) (0,0) 0 0.6 0 0 0 0.1 0 0 0 0
R1 tp3 0 50
C1 tp3 0 10p
""" % (VM_LO, VM_HI)
p=os.path.join(B,"poly_ref.cir"); open(p,"w",encoding="latin-1").write(net)
R,r,ok=run_ng(p,"poly.raw",B,extra="tran 0.5n 400u 300u 0.25n uic\n")
print("poly ok",ok,"rc",r.returncode)
res={}
if ok:
    t=R["time"]; v=R["v(tp3)"]
    m=am_metrics(t,v)
    f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    res["poly"]=dict(VH=m["VH"],VL=m["VL"],m=m["m"],thd=thd)
    print("POLY ref  VH=%.4f Vpp  VL=%.4f Vpp  m=%.2f%%  THD=%.3f%%"%(m["VH"],m["VL"],m["m"],thd))

# --- C4 output impedance at 31 MHz: AC analysis on the frozen oscillator ---
body=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
zin = body.replace("RLOADG out 0 2k","RLOADG out 0 2k\nIAC 0 out AC 1")
p2=os.path.join(B,"c4_z.cir"); open(p2,"w",encoding="latin-1").write(zin)
R2,r2,ok2=run_ng(p2,"c4z.raw",B,extra="ac dec 50 1meg 200meg\n")
print("c4 ac ok",ok2)
if ok2:
    f=R2["frequency"]; vout=R2["v(out)"]
    Zout=vout/(-1.0)   # 1 A injected from 0 into out
    i31=int(np.argmin(abs(np.log10(f)-np.log10(31e6))))
    z=Zout[i31]
    print("C4 output impedance @31MHz = %.1f %+.1f j ohm  (|Z|=%.1f, %.1f deg)"%(
        z.real,z.imag,abs(z),np.degrees(np.angle(z))))
    res["c4_zout"]=dict(f=float(f[i31]),re=float(z.real),im=float(z.imag))
json.dump(res,open(os.path.join(ST,"results","ref_and_zout.json"),"w"),indent=1)
