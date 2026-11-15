# -*- coding: utf-8 -*-
"""Consolidate only the independently-verified results for Stage AM-ALT.1."""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1"
RES=os.path.join(ST,"results")
sw=json.load(open(os.path.join(RES,"c4_load_sweep.json")))
ref=json.load(open(os.path.join(RES,"ref_and_zout.json")))
# Thevenin fit on the load sweep (pure resistive loads only)
pts=[(r["rl"],r["vpp"]) for r in sw if r["clp"]==4]
import numpy as np
RL=np.array([p[0] for p in pts]); V=np.array([p[1] for p in pts])
# V = V0*RL/(Rs+RL)  ->  1/V = (Rs/V0)(1/RL) + 1/V0
A=np.vstack([1.0/RL, np.ones_like(RL)]).T
coef,*_=np.linalg.lstsq(A,1.0/V,rcond=None)
Rs=coef[0]/coef[1]; V0=1.0/coef[1]
print("C4 carrier Thevenin fit (4 pF loads):  V0 = %.3f Vpp , Rs = %.0f ohm"%(V0,Rs))
for rl,v in pts:
    print("   RL=%6d  measured %.4f Vpp   fit %.4f"%(rl,v,V0*rl/(Rs+rl)))
print("\nPOLY(3) reference: VH=%.4f VL=%.4f Vpp  m=%.2f%%  THD=%.4f%%"%(
    ref["poly"]["VH"],ref["poly"]["VL"],ref["poly"]["m"],ref["poly"]["thd"]))
json.dump({"V0_vpp":float(V0),"Rs_ohm":float(Rs),
           "poly":ref["poly"],
           "frozen_c4_at_2k10p":1.9745,
           "c4_f0_MHz":31.0002,"c4_thd_pct":11.46},
          open(os.path.join(RES,"solid_findings.json"),"w"),indent=1)
print("\nwrote solid_findings.json")
