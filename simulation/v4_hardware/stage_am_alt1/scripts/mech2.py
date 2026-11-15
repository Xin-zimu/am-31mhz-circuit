# -*- coding: utf-8 -*-
"""Mechanism probe, sign fixed: base current must flow INTO an NPN base."""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, ST
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
B=os.path.join(ST,"bench","mech2"); os.makedirs(B,exist_ok=True)
def run(tag, ic_ma, rc=1000):
    net="""* mechanism probe
VCC vcc 0 5
Q1 xc xb 0 2N3904
RC1 vcc xc %g
IB xb 0 -%g
VS src 0 AC 1
CIN src xb 1u
"""%(rc, ic_ma*1e-3/200.0)
    p=os.path.join(B,tag+".cir")
    open(p,"w",encoding="latin-1").write(net+MODEL+
      "\n.control\nset filetype=ascii\nop\nprint @q1[ic]\nac dec 3 31meg 31meg\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",B,timeout=200,extra="")
    return R,r
if __name__=="__main__":
    print("CE stage |Av| @31 MHz vs collector current  (Rc=1000, emitter grounded)")
    print(" Ic/mA   |Av|    Rc/re")
    rows=[]
    for ic in (0.25,0.5,1.0,2.0):
        R,r=run("n%d"%(ic*100),ic)
        if R is None: print("  %.2f FAIL"%ic); continue
        g=float(abs(R["v(xc)"][0]))
        print("  %.2f   %7.2f  %8.1f"%(ic,g,1000.0/(26.0/ic)))
        rows.append(dict(ic_mA=ic,gain=g))
    if len(rows)>=2:
        print("\n gain ratio %.2f..%.2f mA: %.2f  (linear-in-Ic: %.2f)"%(
            rows[0]["ic_mA"],rows[-1]["ic_mA"],rows[-1]["gain"]/rows[0]["gain"],
            rows[-1]["ic_mA"]/rows[0]["ic_mA"]))
    json.dump(rows,open(os.path.join(ST,"results","mechanism.json"),"w"),indent=1)
