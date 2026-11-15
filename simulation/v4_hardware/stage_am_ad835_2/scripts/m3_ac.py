# -*- coding: utf-8 -*-
"""Module 3 (redo 2): AC sweeps, fully complex-safe."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod3"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")
HDR={"A":".include ../../models/third_party_GLuisF/ad835.sub\n",
     "B":".include ../../adapted/AD835_Behav.sub\n"}
VSUP="VP VP 0 5\nVN VN 0 -5\n"
def sub(m): return "AD835" if m=="A" else "AD835_BEHAV"
def run_ac(tag,m,drv,rl=150,an=".ac dec 200 1e5 5e8"):
    p=os.path.join(B,"%s_%s.net"%(tag,m))
    open(p,"w",encoding="utf-8").write("* ac\n"+HDR[m]+VSUP+drv+
        "XU X1 X2 Y1 Y2 VN Z W VP %s\nRL W 0 %g\n%s\n.options plotwinsize=0\n.end\n"%(sub(m),rl,an))
    R,lg,rc=run_and_load(p,ascii=True)
    fk=[k for k in R if k.lower()=="frequency"][0]
    return R[fk], R

out={}
for m in "AB":
    f,R=run_ac("X",m,"VX1 X1 0 dc 0 ac 1\nVX2 X2 0 0\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\n")
    H=R[[k for k in R if k.lower()=="v(w)"][0]]
    out["acX_"+m]={"f":[float(x) for x in f],"mag":[float(x) for x in np.abs(H)],
                   "ph":[float(x) for x in np.degrees(np.angle(H))]}
    f2,R2=run_ac("Z",m,"VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 dc 0 ac 1\n")
    H2=R2[[k for k in R2 if k.lower()=="v(w)"][0]]
    out["acZ_"+m]={"f":[float(x) for x in f2],"mag":[float(x) for x in np.abs(H2)],
                   "ph":[float(x) for x in np.degrees(np.angle(H2))]}
    i31=int(np.argmin(abs(np.log10(f)-np.log10(31e6))))
    print("[%s] X DC=%.5f  31MHz |H|=%.5f (%+.3f dB) ph=%+.2f | Z 31MHz |H|=%.5f"%(
        m,float(np.abs(H)[0]),float(np.abs(H)[i31]),float(20*np.log10(np.abs(H)[i31]/np.abs(H)[0])),
        float(np.degrees(np.angle(H))[i31]),float(np.abs(H2)[int(np.argmin(abs(np.log10(f2)-np.log10(31e6))))])))
    # Zin
    p=os.path.join(B,"zin_%s.net"%m)
    open(p,"w",encoding="utf-8").write("* zin\n"+HDR[m]+VSUP+
      "VX1 X1 0 dc 0 ac 1\nVX2 X2 0 0\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\n"
      "XU X1 X2 Y1 Y2 VN Z W VP %s\nRL W 0 150\n.ac dec 50 1e5 5e8\n.options plotwinsize=0\n.end\n"%sub(m))
    Rz,_,_=run_and_load(p,ascii=True)
    fk=[k for k in Rz if k.lower()=="frequency"][0]
    Zin=Rz[[k for k in Rz if k.lower()=="v(x1)"][0]]/(-Rz[[k for k in Rz if k.lower()=="i(vx1)"][0]])
    out["zinX_"+m]={"f":[float(x) for x in Rz[fk]],
                    "zr":[float(x.real) for x in Zin],"zi":[float(x.imag) for x in Zin]}
    iz=int(np.argmin(abs(np.log10(Rz[fk])-np.log10(31e6))))
    print("    Zin(X1)@31MHz = %.1f %+.1f j ohm"%(Zin[iz].real,Zin[iz].imag))

json.dump(out,open(os.path.join(RES,"M3_ac.json"),"w"))
print("\nsaved M3_ac.json")
