# -*- coding: utf-8 -*-
"""Diagnose model B output stage and project convergence."""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw, run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
print("MODEL B output stage:")
print("  B2  W 0 I=table((V(W)-V(i11)), -Ish/1E4,-Ish, Ish/1E4,Ish)   Ish=75mA")
print("  R13 W 0 {Vop/Ish} = 2.5/0.075 = %.3f ohm  <-- PERMANENT shunt at W"%(2.5/0.075))
print("  => open-circuit output resistance is 33.3 ohm, not <1 ohm")
print("  => max |W| into any load = 2.5 * RL/(RL+33.33)")
for RL in (1e9,150,50,25,10):
    print("     RL=%9.0f -> |W|max = %.4f V"%(RL, 2.5*RL/(RL+1000/30)))
print()
print("MODEL A output stage:")
print("  B2 77 0 V=table(V(10),VN,VP)   R7 77 7 0.1  -> 0.1 ohm, hard clamp to rails")
print("  NO current limit at all (bench measured 15 A into 0.1 ohm)")
print()

# Try model B project run with different solver options, short window
B=os.path.join(STAGE,"bench","mod6")
base=open(os.path.join(B,"adB_U105.net"),encoding="utf-8").read()
body=base.split(".options plotwinsize=0")[0]
variants={
 "v1_default": ".tran 0 400u 300u 2n uic",
 "v2_gear":    ".options method=gear\n.tran 0 400u 300u 2n uic",
 "v3_loose":   ".options reltol=1e-3 abstol=1e-9 vntol=1e-4 chgtol=1e-13\n.tran 0 400u 300u 2n uic",
}
for name,an in variants.items():
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotswinsize=0\n"+an+"\n.end\n")
    t0=time.time(); r=run(p,ascii=False,timeout=180); dt=time.time()-t0
    print("%-12s rc=%d %.1fs"%(name,r.returncode,dt))
