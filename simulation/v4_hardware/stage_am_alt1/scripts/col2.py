# -*- coding: utf-8 -*-
"""ALT-1: collector modulator with a proper drive chain.
oscillator 'out' -> EF buffer (solves the 31 MHz low-Zin problem documented in
AM-02.2) -> attenuator -> CE RF stage whose collector load returns to the
modulated rail -> coupling -> load.
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

def stage_collector(rt,rm,rb,  rc=470, rinj=1000, re_ef=680, rh=300, rl=1000, cl=10e-12):
    return """* ---- EF buffer (fixes the 31 MHz low input impedance of a CE stage) ----
C9IN out m9fb 10n
R9C vcc m9fb 22k
R9F m9fb 0 4.7k
Q9B vcc m9fb m9fe 2N3904
R9EB m9fe 0 %g
* ---- RF CE stage; collector load returns to the modulated rail ----
R9S m9fe m9base %g
Q9M m9rail m9col m9emit 2N3904
R9G m9rail m9col %g
R9H m9emit 0 %g
C9BY m9emit 0 10n
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
* ---- 20 kHz -> modulated rail ----
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 470
""" % (re_ef, rinj, rc, rh, rl, cl*1e12, rt, rm, rb)

def net(tag, stage, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC + "\n* ===== %s =====\n" % tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n" % (vmlo, vmhi, duty) +
            stage + MODEL + ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def go(tag, txt, tstop="1.0m", tstart="0.70m", tmax="0.4n", to=1800, verbose=True):
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print(tag,"TIMEOUT",flush=True); return None,None
    if not ok:
        print(tag,"FAIL",flush=True); print(r.stdout[-500:],flush=True); return None,None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    if verbose:
        print("%-14s %.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%%  rail=%.2f..%.2f Vce_min=%.2f"%(
            tag,time.time()-t0,m["VH"],m["VL"],m["m"],fund,thd,
            R["v(m9rail)"].mean(),R["v(m9rail)"].max(),
            (R["v(m9col)"]-R["v(m9emit)"]).min()),flush=True)
    return dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
                rail_min=float(R["v(m9rail)"].min()),rail_max=float(R["v(m9rail)"].max()),
                vce_min=float((R["v(m9col)"]-R["v(m9emit)"]).min()),
                icol_dc=float(((R["v(m9rail)"]-R["v(m9col)"])/470.0).mean())), R

if __name__=="__main__":
    # Vrail must sit well above Vce_sat + swing
    # choose Vrail_lo=2.6, Vrail_hi=4.31 (ratio 1.658) -> Vbase 3.3 .. 5.01: too high for 5 V
    # use a divider ratio that gives Vbase(Vm)=2.55+0.1451*Vm  => Vrail 1.88 .. 3.16
    from scipy.optimize import fsolve
    a,b=2.55,0.1451
    def eqs(p):
        Rt,Rm=p; rb=20e3; G=1/Rt+1/Rm+1/rb
        return [5.0/(Rt*G)-a, 1.0/(Rm*G)-b]
    Rt,Rm=fsolve(eqs,[20e3,30e3])
    print("Rt=%.0f Rm=%.0f Rb=20000"%(Rt,Rm))
    res={}
    st=stage_collector(Rt,Rm,20e3)
    r,_=go("C_ef",net("C_ef",st))
    if r: res["C_ef"]=r
    json.dump(res,open(os.path.join(ST,"results","collector_v2.json"),"w"),indent=1)
