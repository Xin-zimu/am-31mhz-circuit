# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
d=os.path.join(STAGE,"bench")

# --- real C4 crystal netlist ---
c4=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\S04_RF_CARRIER\XTAL\c4_dual_load_20261030\netlists\c4_trap_0p125n_2k_rtol1e5.cir"
print("C4 exists:", os.path.exists(c4))
src=open(c4,encoding="utf-8",errors="replace").read()
print("C4 head:"); print("\n".join(src.splitlines()[:18]))
p=os.path.join(d,"c4_probe.net")
open(p,"w",encoding="utf-8").write(src+"\n.options plotwinsize=0\n.tran 0 2m 1.9m 20n uic\n.end\n")
t0=time.time(); r=run(p, ascii=True); dt=time.time()-t0
print("C4 rc",r.returncode,"%.1fs"%dt)
if r.returncode: print(log(p)[-1500:])
else:
    R=load_raw(os.path.join(d,"c4_probe.raw"))
    print("  vars:", sorted(k for k in R)[:20])
