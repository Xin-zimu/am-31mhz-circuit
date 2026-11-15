# -*- coding: utf-8 -*-
"""ALT-1: parameterised collector modulator + node trace + sweep."""
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
def build(rt,rm,rb, rc=300, a1=3900, a2=100, rbb=10e3, rbc=1.62e3, ref=680, rl=50, cl=10e-12, re_rail=470):
    return """* ---- EF buffer ---- 
C9IN out m9fb 10n
R9C vcc m9fb 22k
R9F m9fb 0 4.7k
Q9B vcc m9fb m9fe 2N3904
R9EB m9fe 0 %g
* ---- attenuator into the RF stage base ----
R9A1 m9fe m9at %g
R9A2 m9at 0 %g
C9B m9at m9base 1n
R9BB vcc m9base %g
R9BC m9base 0 %g
* ---- RF CE stage, emitter grounded, collector load on the modulated rail ----
Q9M m9rail m9col 0 2N3904
R9G m9rail m9col %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
* ---- 20 kHz -> modulated rail ----
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 %g
""" % (ref, a1, a2, rbb, rbc, rc, rl, cl*1e12, rt, rm, rb, re_rail)

def net(tag, st, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC+"\n* ===== %s =====\n"%tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n"%(vmlo,vmhi,duty) +
            st + MODEL + ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def go(tag, txt, tstop="0.8m", tstart="0.60m", tmax="0.4n", to=1200, trace=False):
    B=os.path.join(ST,"bench",tag); os.makedirs(B,exist_ok=True)
    p=os.path.join(B,tag+".cir"); open(p,"w",encoding="latin-1").write(txt)
    t0=time.time()
    try: R,r,ok=run_ng(p,tag+".raw",B,timeout=to,extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    except Exception: print(tag,"TIMEOUT",flush=True); return None
    if not ok: print(tag,"FAIL",flush=True); return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v); f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    vce=(R["v(m9col)"]-0.0)
    print("%-10s %3.0fs VH=%.4f VL=%.4f m=%6.2f%% car=%.4f THD=%5.2f%% Vcol=%.2f..%.2f rail=%.2f..%.2f"%(
        tag,time.time()-t0,m["VH"],m["VL"],m["m"],fund,thd,vce.min(),vce.max(),
        R["v(m9rail)"].min(),R["v(m9rail)"].max()),flush=True)
    if trace:
        T=32/31e6; n=int((t[-1]-t[0])/T)
        def pp(vv):
            a=[]
            for i in range(n):
                mm=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
                if mm.sum()>3: a.append(vv[mm].max()-vv[mm].min())
            return np.percentile(a,97),np.percentile(a,3)
        for k in ("v(m9fe)","v(m9at)","v(m9base)","v(m9col)","v(m9rail)","v(amout)"):
            if k in R:
                hi,lo=pp(R[k]); print("     %-10s dc=%+7.4f  carrier %7.4f / %7.4f Vpp"%(k,R[k].mean(),hi,lo),flush=True)
    return dict(tag=tag,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
                vcol_min=float(vce.min()),vcol_max=float(vce.max()),
                rail_lo=float(R["v(m9rail)"].min()),rail_hi=float(R["v(m9rail)"].max()))

if __name__=="__main__":
    from scipy.optimize import fsolve
    res={}
    def div(a,b,rbot=10e3):
        def eqs(p):
            Rt,Rm=p; G=1/Rt+1/Rm+1/rbot
            return [5.0/(Rt*G)-a, 1.0/(Rm*G)-b]
        Rt,Rm=fsolve(eqs,[15e3,60e3]); return Rt,Rm
    # rail: Vl=2.10, Vh=2.89 -> follower base = rail+0.70
    Rt,Rm=div(2.80, (2.89-2.10)/4.0)
    print("rail divider Rt=%.0f Rm=%.0f"%(Rt,Rm),flush=True)
    always = go("C_a", net("C_a", build(Rt,Rm,10e3)), trace=True)
    if always: res["C_a"]=always
    json.dump(res,open(os.path.join(ST,"results","col_sweep.json"),"w"),indent=1)
