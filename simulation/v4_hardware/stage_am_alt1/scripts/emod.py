# -*- coding: utf-8 -*-
"""ALT-1 emitter modulation, with automatic name-collision avoidance."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, carrier_thd, ST
from guard import check
sys.stdout.reconfigure(encoding="utf-8")
OSC=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
def stage(rm, rb, re, rc, a1=1000, a2=100, rbb=22e3, rbc=4.7e3, rl=1e6, cl=10e-12, ref=680):
    return """* ---- carrier buffer ----
CB1 out fbn 10n
RB0 vcc fbn 22k
RB00 fbn 0 4.7k
QB1 vcc fbn fen 2N3904
RE0 fen 0 %g
RA1 fen at1 %g
RA2 at1 0 %g
* ---- RF CE stage; emitter degenerated into the audio summing node ----
CAB at1 xbn 1n
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 vcc xcn van 2N3904
RC1 vcc xcn %g
RE1 van xen %g
* ---- audio injection (Thevenin: sources AND sinks) ----
RM1 mod van %g
RBX1 van 0 %g
* ---- output ----
CO1 xcn amout 10n
RL1 amout 0 %g
CL1 amout 0 %gp
"""%(ref,a1,a2,rbb,rbc,rc,re,rm,rb,rl,cl*1e12)

def net(tag, st, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC+"\n* ===== %s =====\n"%tag+
            "VMS mod 0 PULSE(%g %g 300u 20n 20n %s 50u)\n"%(vmlo,vmhi,duty)+
            st+MODEL+".options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27\n")

def go(tag,txt,stage_txt_for_check="",tstop="0.90m",tstart="0.75m",tmax="0.5n",to=900):
    bad=check(OSC,stage_txt_for_check)
    if bad: print("%-22s NAME COLLISION %s"%(tag,bad),flush=True); return None
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print("%-22s TIMEOUT"%tag,flush=True); return None
    if not ok:
        print("%-22s FAIL %.0fs"%(tag,time.time()-t0),flush=True)
        for l in r.stdout.splitlines():
            if "Error" in l or "error" in l: print("      ",l.strip(),flush=True)
        return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    d=dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
           van_lo=float(R["v(van)"].min()),van_hi=float(R["v(van)"].max()))
    print("%-22s %2.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%%"%(
        tag,time.time()-t0,d["VH"],d["VL"],d["m"],fund,thd),flush=True)
    return d

if __name__=="__main__":
    res={}
    for (rm,rb,re,rc) in [(6800,470,100,470),(3900,270,100,470),(6800,470,220,470),(8200,560,150,330)]:
        tag="M_%d_%d_%d_%d"%(rm,rb,re,rc)
        st=stage(rm,rb,re,rc); d=go(tag,net(tag,st),st)
        if d: d.update(dict(rm=rm,rb=rb,re=re,rc=rc)); res[tag]=d
    json.dump(res,open(os.path.join(ST,"results","emod_grid.json"),"w"),indent=1)
    print("DONE",len(res),flush=True)
