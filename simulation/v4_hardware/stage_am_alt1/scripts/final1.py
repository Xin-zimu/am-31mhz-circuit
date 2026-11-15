# -*- coding: utf-8 -*-
"""ALT-1 FINAL: emitter (current) modulation, designed from the verified law
    |Av| = Rc / (26mV/Ic) = 38.5 * Ic[mA] * (Rc/1000)
Target m = 24.77% -> Ic_hi/Ic_lo = 1.658.

Vbe is held constant by a stiff base divider; the audio moves the EMITTER:
    Ie = (Vb - Vbe - Ve)/Re   -> linear in Ve  -> linear gain modulation
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
def stage(vb, re, rm, rbx, rc, a1=1000, a2=100, ref=680, rbb=22e3, rbc=4.7e3,
          rl=1e6, cl=10e-12):
    """Base bias fixed by rbb/rbc; audio Thevenin (mod,Rm)-(rbx,gnd) into emitter."""
    return """* ---- carrier buffer ----
CB1 out fbn 10n
RB0 vcc fbn 22k
RB00 fbn 0 4.7k
QB1 vcc fbn fen 2N3904
RE0 fen 0 %g
RA1 fen at1 %g
RA2 at1 0 %g
* ---- audio Thevenin source for the emitter ----
RM1 mod vm1 %g
RBX1 vm1 0 %g
* ---- RF stage: base fixed, emitter on the audio node ----
CAB at1 xbn 1n
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn ven 2N3904
RC1 vcc xcn %g
RE1 ven vm1 %g
* ---- output ----
CO1 xcn amout 10n
RL1 amout 0 %g
CL1 amout 0 %gp
"""%(ref,a1,a2,rm,rbx,rbb,rbc,rc,re,rl,cl*1e12)

def net(tag, st, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC+"\n* ===== %s =====\n"%tag+
            "VMS mod 0 PULSE(%g %g 300u 20n 20n %s 50u)\n"%(vmlo,vmhi,duty)+
            st+MODEL+".options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27\n")

def go(tag,txt,st,tstop="0.90m",tstart="0.75m",tmax="0.5n",to=1200,quiet=False):
    bad=check(OSC,st)
    if bad: print("%-16s COLLISION %s"%(tag,bad),flush=True); return None
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print("%-16s TIMEOUT"%tag,flush=True); return None
    if not ok:
        if not quiet: print("%-16s FAIL"%tag,flush=True)
        return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    d=dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
           vce_min=float((R["v(xcn)"]-R["v(ven)"]).min()), fs=time.time()-t0)
    print("%-16s %2.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%% Vce_min=%.2f"%(
        tag,d["fs"],d["VH"],d["VL"],d["m"],fund,thd,d["vce_min"]),flush=True)
    return d

if __name__=="__main__":
    res={}
    # Vb must give Ic_lo..Ic_hi without saturating: pick Vb=1.05, Re=100
    #   Ve_lo=(Vb-0.65) - Ie*Re ; with the Thevenin the operating point is set by RM1/RBX1
    for (re,rm,rbx,rc) in [(100,22e3,470,1000),(100,22e3,220,1000),(220,22e3,470,1000),
                           (100,10e3,470,1000),(100,22e3,470,2200)]:
        tag="F_%d_%d_%d_%d"%(re,int(rm/1000),rbx,rc)
        st=stage(1.05,re,rm,rbx,rc)
        d=go(tag,net(tag,st),st)
        if d: d.update(dict(re=re,rm=rm,rbx=rbx,rc=rc)); res[tag]=d
    json.dump(res,open(os.path.join(ST,"results","final_grid.json"),"w"),indent=1)
    print("DONE",len(res),flush=True)
