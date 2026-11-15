# -*- coding: utf-8 -*-
"""Module 2 (fixed): clipping, bias, Z load, output swing, slew."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod2"); os.makedirs(B,exist_ok=True)
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
def load(f,mode="dc"):
    return run_and_load(f,ascii=True)

# ---- bias currents via .op ----
print("=== Input bias currents (input at 0 V, other input grounded) ===")
for m in "AB":
    p=write("ibias",m,VSUP+"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",".op\n")
    R,lg,rc=load(p)
    def g(n):
        for k in R:
            if k.lower()==n.lower(): return float(np.atleast_1d(R[k])[0])
        return float('nan')
    vx1,vx2,vy1,vy2,vz = g("I(VX1)"),g("I(VX2)"),g("I(VY1)"),g("I(VY2)"),g("I(VZ)")
    print("[%s] into part: X1=%+8.2f uA  X2=%+8.2f uA  Y1=%+8.2f uA  Y2=%+8.2f uA  Z=%+8.2f uA"%(
        m,-vx1*1e6,-vx2*1e6,-vy1*1e6,-vy2*1e6,-vz*1e6))
    print("      supply: I(VP)=%+.3f mA  I(VN)=%+.3f mA  Pdiss=%.1f mW"%(
        -g("I(VP)")*1e3, -g("I(VN)")*1e3, (5*-g("I(VP)") + 5*-g("I(VN)"))*1e3))
    out["ibias_"+m]={"Ix1":-vx1,"Ix2":-vx2,"Iy1":-vy1,"Iy2":-vy2,"Iz":-vz,
                     "Ivp":-g("I(VP)"),"Ivn":-g("I(VN)")}

# ---- Z differential R ----
print("\n=== Z differential input resistance ===")
for m in "AB":
    p=write("zin",m,VSUP+"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",".dc VZ -0.2 0.2 0.001\n")
    R,_,_=load(p); z=R["V(z)"]; i=-R["I(VZ)"]
    sel=np.abs(z)>1e-6
    Rz=float(np.mean(z[sel]/i[sel]))
    print("[%s] Z diff R = %.2f kOhm   (datasheet 60 kOhm)"%(m,Rz/1e3)); out["Rz_"+m]=Rz

# ---- output swing vs load (DC, Z driven, X=Y=0) ----
print("\n=== Output swing / current limit (Z sweep, X=Y=0) ===")
for m in "AB":
    for RL in (150, 50, 25):
        p=write("swing%d"%RL,m,VSUP+"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 %d\n"%RL,".dc VZ -3 3 0.002\n")
        R,_,_=load(p); w=R["V(w)"]; z=R["V(z)"]
        hi=np.max(w); lo=np.min(w)
        out["swing_%s_%d"%(m,RL)]={"hi":float(hi),"lo":float(lo),"z":z.tolist(),"w":w.tolist()}
        print("[%s] RL=%3d : W+ = %+7.4f V   W- = %+7.4f V   (datasheet +-2.2 min/+-2.5 typ unloaded-ish)"%(m,RL,hi,lo))

# ---- output current limit: short circuit ----
print("\n=== Output short-circuit current (RL=0.1 ohm) ===")
for m in "AB":
    p=write("isc",m,VSUP+"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 0.1\n",".dc VZ -3 3 0.01\n")
    R,_,_=load(p); w=R["V(w)"]
    print("[%s] max |I(W)| = %.2f mA   (datasheet Isc 75 mA typ)"%(m, np.max(np.abs(w))/0.1*1e3))

json.dump(out,open(os.path.join(RES,"M2.json"),"w"))
print("\nsaved M2.json")
