# -*- coding: utf-8 -*-
"""ALT-1: converge on m=24.77% with healthy Vce and maximum output."""
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
def stage(rc,rbt,rbb_,re,rm,rbx,a1,a2,ref=680,rl=1e6,cl=10e-12):
    return """CB1 out fbn 10n
RB0 vcc fbn 22k
RB00 fbn 0 4.7k
QB1 vcc fbn fen 2N3904
RE0 fen 0 %g
RA1 fen at1 %g
RA2 at1 0 %g
RM1 mod vm1 %g
RBX1 vm1 0 %g
CAB at1 xbn 1n
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn ven 2N3904
RC1 vcc xcn %g
RE1 ven vm1 %g
CO1 xcn amout 10n
RL1 amout 0 %g
CL1 amout 0 %gp
"""%(ref,a1,a2,rm,rbx,rbt,rbb_,rc,re,rl,cl*1e12)
def net(tag,st,vmlo=0.0748175,vmhi=4.0748175,duty="4.98u"):
    return (OSC+"\n* ===== %s =====\n"%tag+
            "VMS mod 0 PULSE(%g %g 300u 20n 20n %s 50u)\n"%(vmlo,vmhi,duty)+
            st+MODEL+".options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27\n")
def go(tag,txt,st,tstop="0.90m",tstart="0.75m",tmax="0.5n",to=1200):
    if check(OSC,st): print("%-20s COLLISION"%tag,flush=True); return None
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print("%-20s TIMEOUT"%tag,flush=True); return None
    if not ok: print("%-20s FAIL"%tag,flush=True); return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    vce=float((R["v(xcn)"]-R["v(ven)"]).min())
    d=dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,vce_min=vce,
           vc_dc=float(R["v(xcn)"].mean()))
    print("%-20s %2.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%% Vc_dc=%.2f Vce_min=%.2f"%(
        tag,time.time()-t0,d["VH"],d["VL"],d["m"],fund,thd,d["vc_dc"],vce),flush=True)
    return d
if __name__=="__main__":
    res={}
    for (rbt,rbb_,rc,re,rm,rbx,a1,a2) in [
        (6.8e3,4.7e3,1000,100,22e3,1000,220,47),
        (6.8e3,4.7e3,1000,100,33e3,1000,220,47),
        (8.2e3,4.7e3,1000,100,33e3,1500,220,47),
        (6.8e3,4.7e3,1000,100,47e3,1500,220,47),
        (5.6e3,4.7e3,1000,100,33e3,1000,220,47),
        (6.8e3,4.7e3,1500,150,33e3,1000,220,47),
    ]:
        tag="K_%d_%d_%d_%d"%(int(rbt/100),rc,int(rm/1000),rbx)
        st=stage(rc,rbt,rbb_,re,rm,rbx,a1,a2)
        d=go(tag,net(tag,st),st)
        if d: d.update(dict(rbt=rbt,rbb=rbb_,rc=rc,re=re,rm=rm,rbx=rbx,a1=a1,a2=a2)); res[tag]=d
    json.dump(res,open(os.path.join(ST,"results","converge.json"),"w"),indent=1)
    ok=[(v["m"],k,v["VH"]) for k,v in res.items() if abs(v["m"]-24.77)<3]
    print("\nwithin +-3pp of 24.77%%: ",sorted(ok,reverse=True)[:4],flush=True)
