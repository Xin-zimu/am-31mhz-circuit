# -*- coding: utf-8 -*-
"""ALT-1 consolidated: correct bias helper + emitter modulator AC & transient.

Divider fix: for Vb from Vcc with Rb to ground,
    Rb/(Rt+Rb) = Vb/Vcc  ->  Rt = Rb*(Vcc-Vb)/Vb
"""
import os, sys, json, time, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, carrier_thd, ST
from guard import check
OSC=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
def rt_for(vb, rb, vcc=5.0):
    return rb*(vcc-vb)/vb

# ---------- AC: verify the RF stage really amplifies ----------
Bac=os.path.join(ST,"bench","ac2"); os.makedirs(Bac,exist_ok=True)
def ac_run(tag, rc, re1, rs, vb, rb=4.7e3):
    net="""VCC vcc 0 5
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va vae %g
RBX1 vae 0 1k
VS ac 0 AC 1
RS ac xbn %g
CAB ac xbn 1n
"""%(rt_for(vb,rb),rb,rc,re1,rs)
    p=os.path.join(Bac,tag+".cir")
    open(p,"w",encoding="latin-1").write(net+MODEL+
      "\n.control\nset filetype=ascii\nac dec 20 1meg 100meg\nwrite %s.raw all\nquit\n.endc\n.end\n"%tag)
    R,r,ok=run_ng(p,tag+".raw",Bac,timeout=300,extra="")
    return R

if __name__=="__main__":
    print("=== RF stage |Av| @31 MHz (bias bug fixed) ===")
    rows=[]
    for vb in (0.70,0.75,0.80):
        for rc in (470,1000,2200):
            for re1 in (10,47):
                R=ac_run("b_%d_%d_%d"%(int(vb*100),rc,re1),rc,re1,50,vb)
                if R is None: print("  FAIL"); continue
                f=np.real(R["frequency"]); v=R["v(xcn)"]
                i=int(np.argmin(abs(np.log10(abs(f))-np.log10(31e6))))
                g=abs(v[i])
                rows.append((g,vb,rc,re1))
                print("  Vb=%.2f Rc=%5g Re1=%3g -> |Av|=%7.2f (%.1f dB)"%(vb,rc,re1,g,20*np.log10(max(g,1e-9))))
    rows.sort(reverse=True)
    print("\nbest gains:",[(round(g,1),vb,rc,re1) for g,vb,rc,re1 in rows[:6]])
    json.dump([{"gain":g,"vb":vb,"rc":rc,"re1":re1} for g,vb,rc,re1 in rows],
              open(os.path.join(ST,"results","ce_ac2.json"),"w"),indent=1)
