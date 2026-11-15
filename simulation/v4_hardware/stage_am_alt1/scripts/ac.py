# -*- coding: utf-8 -*-
"""ALT-1: AC characterisation of the 31 MHz CE RF stage (model appended)."""
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
B=os.path.join(ST,"bench","ac"); os.makedirs(B,exist_ok=True)
def run(tag, net):
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(net+MODEL+
        "\n.control\nset filetype=ascii\nac dec 20 1meg 100meg\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",B,timeout=300,extra="")
    return R

def ce_ac(rc, re1, rs, vb):
    rt=(vb/(5-vb))*4.7e3
    return """VCC vcc 0 5
RB01 vcc xbn %g
RB02 xbn 0 4.7k
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va vae %g
RBX1 vae 0 1k
VS ac 0 AC 1
RS ac xbn %g
CAB ac xbn 1n
"""%(rt,rc,re1,rs)

if __name__=="__main__":
    out={}
    print("RF CE stage: |Av| at 31 MHz, and Vce")
    best=[]
    for vb in (0.80,0.90,1.00):
        for rc in (470,1000,2200):
            for re1 in (10,47,100):
                tag="a_%d_%d_%d"%(int(vb*100),rc,re1)
                R=run(tag, ce_ac(rc,re1,50,vb))
                if R is None: print("  %s FAIL"%tag); continue
                f=R["frequency"]; v=R["v(xcn)"]
                i=int(np.argmin(abs(np.log10(f)-np.log10(31e6))))
                g=abs(v[i])
                out[tag]=dict(vb=vb,rc=rc,re1=re1,gain=float(g))
                print("  Vb=%.2f Rc=%5g Re1=%3g -> |Av|@31M=%7.2f (%.1f dB)"%(vb,rc,re1,g,20*np.log10(max(g,1e-9))))
                best.append((g,vb,rc,re1))
    best.sort(reverse=True)
    print("\nstrongest:",best[:5])
    json.dump(out,open(os.path.join(ST,"results","ce_ac.json"),"w"),indent=1)
