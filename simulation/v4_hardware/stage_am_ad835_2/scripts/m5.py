# -*- coding: utf-8 -*-
"""Module 5: transient - slew rate, feedthrough, 5us pulse, output distortion, power."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod5"); os.makedirs(B,exist_ok=True)
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

# ---- Slew rate: X step, Y=1 -> W step 0..2 V ----
print("=== Slew rate (Y=1V, X steps -1 -> +1, W should go -1 -> +1) ===")
for m in "AB":
    p=write("slew",m,VSUP+
      "VX1 X1 0 PULSE(-1 1 1u 1n 1n 5u 10u)\nVX2 X2 0 0\nVY1 Y1 0 1\nVY2 Y2 0 0\nVZ Z 0 0\nRL W 0 150\n",
      ".tran 0 6u 0 0.2n\n")
    R,lg,rc=run_and_load(p,ascii=True)
    t=R["time"]; w=R["V(w)"]
    sel=(t>0.9e-6)&(t<2.0e-6)
    tt=t[sel]; ww=w[sel]
    i10=np.argmax(ww>0.2*(ww[-1]-ww[0])+ww[0]); i90=np.argmax(ww>0.9*(ww[-1]-ww[0])+ww[0])
    tr=tt[i90]-tt[i10]
    dmax=np.max(np.gradient(ww,tt))/1e6
    print("[%s] W: %.4f -> %.4f V, 10-90%% tr=%.3f ns, max dV/dt=%.1f V/us (datasheet 1000 V/us)"%(
        m,ww[0],ww[-1],tr*1e9,dmax))
    out["slew_"+m]={"tr":float(tr),"maxdvdt":float(dmax),"w0":float(ww[0]),"w1":float(ww[-1])}

# ---- Input feedthrough: X=+-1, Y=0 -> W residual ; Y=+-1, X=0 ----
print("\n=== Feedthrough (f=1 MHz, RL=150) ===")
for m in "AB":
    for ch in ("X","Y"):
        if ch=="X":
            drv="VX1 X1 0 SIN(0 1 1meg)\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\n"
        else:
            drv="VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 SIN(0 1 1meg)\nVY2 Y2 0 0\n"
        p=write("ft%s"%ch,m,VSUP+drv+"VZ Z 0 0\nRL W 0 150\n",".tran 0 20u 10u 5n\n")
        R,lg,rc=run_and_load(p,ascii=True)
        t=R["time"]; w=R["V(w)"]; v=R["V(%s1)"%(ch.lower())]
        n=len(t)
        # fit fundamental at 1 MHz over the saved window
        win=slice(n//2,None); tt=t[win]; ww=w[win]
        A=np.column_stack([np.sin(2*np.pi*1e6*tt), np.cos(2*np.pi*1e6*tt), np.ones_like(tt)])
        c,*_=np.linalg.lstsq(A,ww,rcond=None)
        amp=np.hypot(c[0],c[1])
        print("[%s] %s feedthrough: |W_1MHz| = %.5f V for 1 V input -> %+7.2f dB  (datasheet %s)"
              %(m,ch,amp,20*np.log10(amp), "-46 dB" if ch=="X" else "-60 dB"))
        out["ft_%s_%s"%(m,ch)]=float(amp)

json.dump(out,open(os.path.join(RES,"M5.json"),"w"))
print("\nsaved M5.json")
