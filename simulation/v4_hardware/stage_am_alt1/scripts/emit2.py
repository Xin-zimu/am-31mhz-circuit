# -*- coding: utf-8 -*-
"""ALT-1: emitter modulation, corrected topology.
The follower Q9D drives node E directly; Q9M's emitter ties to that same node
(no series resistor to a separate rail).  Then
    Ie(Q9M) = (Vb - Vbe - V(E))/Rload_of_E
and the CE gain tracks Ie linearly -> true AM.
"""
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
def divider(a,b,rb):
    k=1.0-a/5.0-b
    if k<=1e-6: raise ValueError("infeasible a=%.3f b=%.3f"%(a,b))
    G=1.0/(rb*k); return 5.0/(a*G), 1.0/(b*G), rb

def build(rt,rm,rb, rc=470, re_mod=22, rbb=22e3, rbc=6.8e3, a1=1000, a2=100, rl=50, cl=10e-12, re_f=680):
    return """* ---- EF buffer ----
C9IN out m9fb 10n
R9C vcc m9fb 22k
R9F m9fb 0 4.7k
Q9B vcc m9fb m9fe 2N3904
R9EB m9fe 0 %g
* ---- attenuator ----
R9A1 m9fe m9at %g
R9A2 m9at 0 %g
* ---- CE RF stage; emitter tied straight to the modulated node ----
C9B m9at m9base 1n
R9BB vcc m9base %g
R9BC m9base 0 %g
Q9M vcc m9col m9E 2N3904
R9G vcc m9col %g
* ---- follower drives node m9E (emitter load sets the RF stage bias) ----
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9E 2N3904
R9E m9E 0 %g
* ---- output ----
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
"""%(re_f,a1,a2,rbb,rbc,rc,rt,rm,rb,re_mod,rl,cl*1e12)

def net(tag,st,vmlo=0.0748175,vmhi=4.0748175,duty="4.98u"):
    return (OSC+"\n* ===== %s =====\n"%tag+
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n"%(vmlo,vmhi,duty)+
            st+MODEL+".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def go(tag,txt,tstop="0.75m",tstart="0.60m",tmax="0.4n",to=900,trace=False):
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print("%-14s TIMEOUT"%tag,flush=True); return None
    if not ok: print("%-14s FAIL"%tag,flush=True); return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    d=dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
           E_lo=float(R["v(m9e)"].min()),E_hi=float(R["v(m9e)"].max()),
           vce_min=float(R["v(m9col)"].min()), fs=time.time()-t0)
    print("%-16s %2.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%% E=%.2f..%.2f Vc_min=%.2f"%(
        tag,d["fs"],d["VH"],d["VL"],d["m"],fund,thd,d["E_lo"],d["E_hi"],d["vce_min"]),flush=True)
    if trace:
        for k in ("v(m9base)","v(m9E)","v(m9col)","v(m9fe)"):
            if k in R: print("      %-9s dc=%+7.4f min=%+7.4f max=%+7.4f"%(k,R[k].mean(),R[k].min(),R[k].max()),flush=True)
    return d

if __name__=="__main__":
    res={}
    for re_mod in (22,47,100):
        Rt,Rm,Rb=divider(0.95,0.145,10e3) if False else (None,None,None)
        # base of follower must be V(E)+0.7 ; V(E) ~ 0.55..0.90 (mean Ie ~1 mA over re_mod)
        # choose V(E) = 0.55 + 0.070*Vm  (0.55..0.83)
        Rt,Rm,Rb=divider(1.25,0.070,10e3)
        for rc in (470,1000):
            tag="E2_%d_%d"%(rc,re_mod)
            d=go(tag,net(tag,build(Rt,Rm,Rb,rc=rc,re_mod=re_mod)),trace=(re_mod==22 and rc==470))
            if d:
                d.update(dict(Rt=Rt,Rm=Rm,rc=rc,re_mod=re_mod)); res[tag]=d
    json.dump(res,open(os.path.join(ST,"results","emitter_grid2.json"),"w"),indent=1)
    print("DONE",len(res),flush=True)
