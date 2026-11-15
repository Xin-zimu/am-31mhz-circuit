# -*- coding: utf-8 -*-
"""One decisive check: is a CE stage's gain actually current-controlled at 31 MHz?
This settles the mechanism question with data instead of assertion."""
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
B=os.path.join(ST,"bench","mech"); os.makedirs(B,exist_ok=True)
def run(tag, ic_ma, rc=1000):
    """Force the collector current with a current source, measure small-signal gain."""
    net="""* mechanism probe
VCC vcc 0 5
Q1 xc xb 0 2N3904
RC1 vcc xc %g
IB xb 0 %g
VS src 0 AC 1
CIN src xb 1u
"""%(rc, ic_ma*1e-3/200.0)
    p=os.path.join(B,tag+".cir")
    open(p,"w",encoding="latin-1").write(net+MODEL+
      "\n.control\nset filetype=ascii\nac dec 5 31meg 31meg\nop\nprint @q1[ic]\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",B,timeout=200,extra="")
    return R,r
if __name__=="__main__":
    print("CE stage gain vs collector current (Rc=1000, emitter grounded)")
    print(" Ic/mA    |Av|@31MHz    Rc/re predicted")
    rows=[]
    for ic in (0.5,1.0,2.0,4.0):
        R,r=run("m%d"%(ic*10),ic)
        if R is None: print("  %.1f  FAIL"%ic); continue
        v=R["v(xc)"]; g=float(abs(v[0]))
        re=26.0/ic
        pred=1000.0/re
        print("  %.1f     %8.2f      %8.1f"%(ic,g,pred))
        rows.append(dict(ic_mA=ic,gain=g,pred=pred))
    json.dump(rows,open(os.path.join(ST,"results","mechanism.json"),"w"),indent=1)
    if len(rows)>=2:
        g1,g2=rows[0]["gain"],rows[-1]["gain"]
        print("\n gain ratio over %.1f..%.1f mA = %.2f  (linear-in-Ic predicts %.2f)"%(
            rows[0]["ic_mA"],rows[-1]["ic_mA"],g2/g1,rows[-1]["ic_mA"]/rows[0]["ic_mA"]))
