# -*- coding: utf-8 -*-
"""Corrected design: Rt=23.5k, Rm=30.3k, Rb=20k -> Vbase(Vm)=2.755+0.1451*Vm."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, carrier_thd, ST
sys.stdout.reconfigure(encoding="utf-8")
OSC=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
MODEL = """
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""

def collector(rt=23.5e3, rm=30.3e3, rb=20e3, rc=470, re=470, re2=100, rl=50, cl=10e-12):
    return """* --- collector modulation: Vrail = 2.08 + 0.148*Vm (design) ---
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 %g
C9IN out m9base 1n
R9C vcc m9base 22k
R9F m9base 0 4.7k
Q9M m9rail m9col m9emit 2N3904
R9G m9rail m9col %g
R9H m9emit 0 %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
""" % (rt,rm,rb,re,rc,re2,rl,cl*1e12)

def net(tag, stage, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC + "\n* ===== %s =====\n" % tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n" % (vmlo, vmhi, duty) +
            stage + MODEL + ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def go(tag, nettext, tstop="1.0m", tstart="0.7m", tmax="0.4n", to=1800):
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(nettext)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print(tag,"TIMEOUT",flush=True); return None
    if not ok:
        print(tag,"FAIL",flush=True); print(r.stdout[-600:],flush=True); return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    print("%-12s %.0fs VH=%.4f VL=%.4f m=%6.2f%% carrier=%.4f THD=%.2f%%"%(
        tag,time.time()-t0,m["VH"],m["VL"],m["m"],fund,thd),flush=True)
    print("        Vrail=%.3f..%.3f  Vcol=%.3f..%.3f  Vce_min=%.3f"%(
        R["v(m9rail)"].mean(),R["v(m9rail)"].max(),R["v(m9col)"].mean(),
        R["v(m9col)"].max(), (R["v(m9col)"]-R["v(m9emit)"]).min()),flush=True)
    return dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd)

if __name__=="__main__":
    res={}
    for rt,rm,rb,tag in [(23.5e3,30.3e3,20e3,"C_v1"),
                         (22e3,27e3,20e3,"C_v2"),
                         (26e3,36e3,22e3,"C_v3")]:
        st=collector(rt,rm,rb)
        r=go(tag,net(tag,st))
        if r: res[tag]=r
    json.dump(res,open(os.path.join(ST,"results","collector_sweep.json"),"w"),indent=1)
    print("saved",flush=True)
