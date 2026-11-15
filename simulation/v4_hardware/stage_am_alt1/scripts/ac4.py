# -*- coding: utf-8 -*-
"""AC check with the mandatory title line (first netlist line is the title)."""
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
B=os.path.join(ST,"bench","ac4"); os.makedirs(B,exist_ok=True)
def rt_for(vb,rb=4.7e3,vcc=5.0): return rb*(vcc-vb)/vb
def ac_run(tag,rc,re1,rs,vb,rb=4.7e3,cin=True):
    net="""* AC probe
VCC vcc 0 5
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va 0 %g
VS src 0 AC 1
RS src xbn %g
%s
"""%(rt_for(vb,rb),rb,rc,re1,rs,("CAB src xbn 1n" if cin else ""))
    p=os.path.join(B,tag+".cir")
    open(p,"w",encoding="latin-1").write(net+MODEL+
      "\n.control\nset filetype=ascii\nac dec 20 1meg 100meg\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",B,timeout=300,extra="")
    return R
if __name__=="__main__":
    rows=[]
    print("=== RF CE stage, correct netlist ===")
    for vb in (0.68,0.72,0.78):
        for rc in (470,1000,2200):
            tag="d_%d_%d"%(int(vb*100),rc)
            R=ac_run(tag,rc,100,50,vb)
            if R is None: print("  FAIL",tag); continue
            f=np.real(R["frequency"]); vc=R["v(xcn)"]; vb_=R["v(xbn)"]; vv=R["v(vcc)"]
            i=int(np.argmin(abs(np.log10(abs(f))-np.log10(31e6))))
            g=abs(vc[i]); gb=abs(vb_[i])
            rows.append(dict(tag=tag,vb=vb,rc=rc,gain=float(g),vbn=float(gb),vcc=float(abs(vv[i]))))
            print("  Vb=%.2f Rc=%5g -> |Vc|=%8.3f |Vb|=%6.3f |Vcc|=%6.3f  Av=Vc/Vb=%.1f (%.1f dB)"%(
                vb,rc,g,gb,abs(vv[i]),g/gb if gb>0 else 0,20*np.log10(max(g/gb,1e-9))))
    json.dump(rows,open(os.path.join(ST,"results","ce_ac4.json"),"w"),indent=1)
