# -*- coding: utf-8 -*-
"""Module 4: Z input, differential usability, slew, offset, feedthrough, pulse, power."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod4"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")
HDR={"A":"* modelA\n.include ../../models/third_party_GLuisF/ad835.sub\n",
     "B":"* modelB\n.include ../../adapted/AD835_Behav.sub\n"}
def inst(m): return "XU X1 X2 Y1 Y2 VN Z W VP %s\n"%("AD835" if m=="A" else "AD835_BEHAV")
def write(tag,m,extra,an):
    p=os.path.join(B,"%s_%s.net"%(tag,m))
    open(p,"w",encoding="utf-8").write(HDR[m]+extra+inst(m)+an+".options plotwinsize=0\n")
    return p
VSUP="VP VP 0 5\nVN VN 0 -5\n"
out={}

def oprun(tag,m,extra):
    p=write(tag,m,VSUP+extra,".op\n")
    R,lg,rc=run_and_load(p,ascii=True)
    def g(n):
        for k in R:
            if k.lower()==n.lower(): return float(np.atleast_1d(R[k])[0])
        return float('nan')
    return g

# ---- Z single-ended input resistance ----
print("=== Z input resistance (Z driven, X=Y=0) ===")
for m in "AB":
    g=oprun("zr",m,"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0.5\nRL W 0 150\n")
    iz=g("I(VZ)")
    print("[%s] V(Z)=0.5V, I into part = %+8.3f uA -> Rz = %6.2f kOhm"%(m,-iz*1e6, 0.5/(-iz)/1e3))
    out["Rz_"+m]=0.5/(-iz)

# ---- differential X2 usability ----
print("\n=== Can X2 be driven? (X1=0, X2=+0.5 V, Y=1) ===")
for m in "AB":
    g=oprun("diff",m,"VX1 X1 0 0\nVX2 X2 0 0.5\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n")
    print("[%s] V(X2)=%+8.4f V (commanded +0.5)  W=%+8.4f V  (expect W=-0.5 if differential works)"%(
        m, g("V(X2)"), g("V(W)")))

# ---- output offset (X=Y=Z=0) ----
print("\n=== Output offset Vos (X=Y=Z=0, RL=150) ===")
for m in "AB":
    g=oprun("vos",m,"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n")
    print("[%s] V(W) = %+8.5f V   (datasheet output offset typ +-25 mV, max +-75 mV)"%(m,g("V(W)")))
    out["Vos_"+m]=g("V(W)")

# ---- quiescent supply current & dissipation ----
print("\n=== Quiescent supply current / dissipation ===")
for m in "AB":
    g=oprun("iq",m,"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n")
    ip=g("I(VP)"); iN=g("I(VN)")
    print("[%s] I(VP)=%+8.3f mA  I(VN)=%+8.3f mA  -> Ptot=%.2f mW  (datasheet 16 mA typ / 25 mA max)"
          %(m,-ip*1e3,-iN*1e3, 5*(-ip)+5*(-iN)))
    out["Iq_"+m]={"Ip":-ip,"In":-iN,"P":5*(-ip)+5*(-iN)}

json.dump(out,open(os.path.join(RES,"M4.json"),"w"))
print("\nsaved M4.json")
