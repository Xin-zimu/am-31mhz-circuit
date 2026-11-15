# -*- coding: utf-8 -*-
"""Time model B in a small bench to find a workable solver setting."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","perf"); os.makedirs(B,exist_ok=True)

def bench(name, opts, tstop="50u", tstep="2n"):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write("""* perf bench model B
.include ../../adapted/AD835_Behav.sub
VADP ADP 0 5
VADN ADN 0 -5
VY1 Y1 0 SIN(0 1 31meg)
VY2 Y2 0 0
VX1 X1 0 PULSE(-1 1 0 1n 1n 25u 50u)
VX2 X2 0 0
VZ  Z  0 0
XU X1 X2 Y1 Y2 ADN Z W ADP AD835_BEHAV
RL W 0 150
%s
.options plotwinsize=0
.tran 0 %s 0 %s
.end
""" % (opts, tstop, tstep))
    t0=time.time(); r=run(p, ascii=False); dt=time.time()-t0
    ok = r.returncode==0
    print("%-28s rc=%d  %6.2f s %s"%(name, r.returncode, dt, "" if ok else "<-- FAIL"))
    if not ok: print("   ", log(p).strip().splitlines()[-1])
    return dt, ok

bench("b_default", "")
bench("b_gear",    ".options method=gear")
bench("b_loose",   ".options reltol=1e-3 abstol=1e-9 vntol=1e-4")
bench("b_gear_loose", ".options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-4")
