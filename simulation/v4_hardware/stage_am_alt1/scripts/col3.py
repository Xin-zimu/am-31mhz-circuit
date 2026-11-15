# -*- coding: utf-8 -*-
"""ALT-1: final collector modulator design.
Chain: oscillator out -> EF buffer -> 39:1 attenuator -> CE RF stage
       (collector load returned to the modulated rail) -> 10n -> 50 ohm || 10 pF
Collector-modulation design:
  Vk = Vce_min + Ve ;  Ic = (Vrail - Vk)/Rc ;  (Vh-Vk)/(Vl-Vk) = 1.658
  chosen: Ve=0.5, Vce_min=0.9, Vl=3.30, Vh=4.55, Rc=300 -> Ic 3.0/4.97 mA
  Vbase(Q9M) = Ve+0.65 = 1.15 V (fixed)
  follower base  = Vrail + 0.70  -> 2.55 .. 3.38 V  ... but follower drop under
  load; solve the divider numerically against the simulated operating point.
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
def stage(rt, rm, rb,  rc=300, att1=3900, att2=100, ref=680, rl=50, cl=10e-12):
    return """* ---- EF buffer: isolates the 31 MHz low CE input impedance ----
C9IN out m9fb 10n
R9C vcc m9fb 22k
R9F m9fb 0 4.7k
Q9B vcc m9fb m9fe 2N3904
R9EB m9fe 0 %g
* ---- attenuator 39:1 into the RF stage ----
R9A1 m9fe m9at %g
R9A2 m9at 0 %g
* ---- RF CE stage; collector load returns to the modulated rail ----
C9B m9at m9base 1n
R9BB vcc m9base 100k
R9BC m9base 0 22k
Q9M m9rail m9col m9emit 2N3904
R9G m9rail m9col %g
R9H m9emit 0 100
C9BY m9emit 0 10n
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
* ---- 20 kHz -> modulated rail ----
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 %g
""" % (ref, att1, att2, rc, rl, cl*1e12, rt, rm, rb, rl)

def net(tag, stage_txt, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC + "\n* ===== %s =====\n" % tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n" % (vmlo, vmhi, duty) +
            stage_txt + MODEL + ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def go(tag, txt, tstop="1.0m", tstart="0.70m", tmax="0.4n", to=1800):
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print(tag,"TIMEOUT",flush=True); return None,None
    if not ok:
        print(tag,"FAIL",flush=True)
        print(r.stdout[-700:],flush=True); return None,None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    vce=(R["v(m9col)"]-R["v(m9emit)"])
    print("%-10s %.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%% Vce_min=%.2f rail=%.2f..%.2f"%(
        tag,time.time()-t0,m["VH"],m["VL"],m["m"],fund,thd,vce.min(),
        R["v(m9rail)"].min(),R["v(m9rail)"].max()),flush=True)
    return dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
                vce_min=float(vce.min()),rail_lo=float(R["v(m9rail)"].min()),
                rail_hi=float(R["v(m9rail)"].max())), R

if __name__=="__main__":
    from scipy.optimize import fsolve
    # follower base must be Vrail+0.7 -> 4.0 .. 5.25 (too high). Reduce Vrail:
    # keep Ic*Rc = 0.9 V and Vce_min 0.9: Vrail_lo = Vk + Ic_lo*Rc = 1.4+0.9 = 2.3
    # Vh = 1.658*2.3 - 0.658*1.4 = 3.81-0.92 = 2.89
    Vl, Vh = 2.30, 2.89
    a, b = Vl+0.70, (Vh-Vl)/4.0
    def eqs(p):
        Rt,Rm=p; rb=10e3; G=1/Rt+1/Rm+1/rb
        return [5.0/(Rt*G)-a, 1.0/(Rm*G)-b]
    Rt,Rm=fsolve(eqs,[15e3,60e3])
    print("follower divider Rt=%.0f Rm=%.0f Rb=10000 ; Vbase=%.2f+%.4f*Vm"%(Rt,Rm,a,b))
    res={}
    r,_=go("C_final", net("C_final", stage(Rt,Rm,10e3)))
    if r: res["C_final"]=r
    json.dump(res,open(os.path.join(ST,"results","collector_final.json"),"w"),indent=1)
