# -*- coding: utf-8 -*-
"""AC check with the source node renamed (node named 'ac' collided with the
analysis type and made ngspice return the source voltage as every node)."""
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
B=os.path.join(ST,"bench","ac3"); os.makedirs(B,exist_ok=True)
def rt_for(vb,rb=4.7e3,vcc=5.0): return rb*(vcc-vb)/vb
def ac_run(tag,rc,re1,rs,vb,rb=4.7e3):
    net="""VCC vcc 0 5
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va vae %g
RBX1 vae 0 1k
VS src 0 AC 1
RS src xbn %g
"""%(rt_for(vb,rb),rb,rc,re1,rs)
    p=os.path.join(B,tag+".cir")
    open(p,"w",encoding="latin-1").write(net+MODEL+
      "\n.control\nset filetype=ascii\nac dec 20 1meg 100meg\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",B,timeout=300,extra="")
    return R
if __name__=="__main__":
    rows=[]
    for vb in (0.68,0.72,0.78):
        for rc in (470,1000,2200):
            for re1 in (10,47,100):
                tag="c_%d_%d_%d"%(int(vb*100),rc,re1)
                R=ac_run(tag,rc,re1,50,vb)
                if R is None: continue
                f=np.real(R["frequency"]); v=R["v(xcn)"]; vb_=R["v(xbn)"]
                i=int(np.argmin(abs(np.log10(abs(f))-np.log10(31e6))))
                g=abs(v[i]); gb=abs(vb_[i])
                rows.append((g,vb,rc,re1,gb))
                print("  Vb=%.2f Rc=%5g Re1=%3g -> |Av|=%8.2f (%.1f dB)  |Vb_node|=%.3f"%(
                    vb,rc,re1,g,20*np.log10(max(g,1e-9)),gb))
    rows.sort(reverse=True)
    print("\nbest:",[(round(r[0],1),r[1],r[2],r[3]) for r in rows[:6]])
    json.dump([{"gain":r[0],"vb":r[1],"rc":r[2],"re1":r[3],"vbn":r[4]} for r in rows],
              open(os.path.join(ST,"results","ce_ac3.json"),"w"),indent=1)
