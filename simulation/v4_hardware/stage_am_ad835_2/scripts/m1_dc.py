# -*- coding: utf-8 -*-
"""Module 1: basic admission tests for both AD835 models."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load, load_raw, run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod1"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results"); os.makedirs(RES,exist_ok=True)

HDR = {
 "A": "* Model A: ad835.sub (LTspice .subckt, 8 nodes = datasheet pins 1..8)\n.include ../../models/third_party_GLuisF/ad835.sub\n",
 "B": "* Model B: AD835_Behav.sub adapter (equations verbatim from the .asc)\n.include ../../adapted/AD835_Behav.sub\n",
}
def inst(m, name="XU"):
    if m=="A": return "%s X1 X2 Y1 Y2 VN Z W VP AD835\n" % name
    return "%s X1 X2 Y1 Y2 VN Z W VP AD835_BEHAV\n" % name

def write(tag, m, extra, analysis):
    p=os.path.join(B,"%s_%s.net"%(tag,m))
    open(p,"w",encoding="utf-8").write(HDR[m]+extra+inst(m)+analysis+".options plotwinsize=0\n")
    return p

VSUP = "VP VP 0 5\nVN VN 0 -5\n"

res={}

# ---- T1: DC transfer W(X) with Y=1, Z=0 ----
for m in "AB":
    p=write("t1_dcx", m, VSUP+
        "VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",
        ".dc VX1 -2 2 0.002\n")
    R,lg,rc = run_and_load(p, ascii=True)
    x=R["V(x1)"]; w=R["V(w)"]
    res["T1_dcX_"+m]={"x":x.tolist(),"w":w.tolist()}
    # slope over +-1V
    sel=(x>=-1)&(x<=1)
    k=np.polyfit(x[sel],w[sel],1)[0]
    print("[%s] T1 DC W(X)@Y=1,Z=0 : slope=%.6f V/V  (ideal U=1.05 -> %.6f)"%(m,k,1/1.05))
    print("     W at X=0: %.6f   W(+1)=%.6f  W(-1)=%.6f"%(np.interp(0,x,w),np.interp(1,x,w),np.interp(-1,x,w)))

# ---- T2: DC transfer W(Y) with X=1 ----
for m in "AB":
    p=write("t2_dcy", m, VSUP+
        "VX1 X1 0 1\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",
        ".dc VY1 -2 2 0.002\n")
    R,lg,rc=run_and_load(p, ascii=True)
    y=R["V(y1)"]; w=R["V(w)"]; sel=(y>=-1)&(y<=1)
    k=np.polyfit(y[sel],w[sel],1)[0]
    print("[%s] T2 DC W(Y)@X=1,Z=0 : slope=%.6f"%(m,k))
    res["T2_dcY_"+m]={"y":y.tolist(),"w":w.tolist()}

# ---- T3: DC transfer W(Z) with X=Y=0 ----
for m in "AB":
    p=write("t3_dcz", m, VSUP+
        "VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",
        ".dc VZ -2 2 0.002\n")
    R,lg,rc=run_and_load(p, ascii=True)
    z=R["V(z)"]; w=R["V(w)"]; sel=(np.abs(z)<=1)
    k=np.polyfit(z[sel],w[sel],1)[0]
    print("[%s] T3 DC W(Z)@X=Y=0 : slope=%.6f (ideal 1.000)"%(m,k))
    res["T3_dcZ_"+m]={"z":z.tolist(),"w":w.tolist()}

json.dump(res, open(os.path.join(RES,"M1_dc.json"),"w"))
print("\nsaved")
