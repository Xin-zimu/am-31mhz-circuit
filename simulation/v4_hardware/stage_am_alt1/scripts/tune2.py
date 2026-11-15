# -*- coding: utf-8 -*-
"""ALT-1: tune the audio attenuator for m = 24.77% (Ic ratio 1.658), then build
the full chain on the real oscillator and characterise it."""
import os, sys, subprocess, json, time, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, carrier_thd, ST
from guard import check
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
B=os.path.join(ST,"bench","op"); os.makedirs(B,exist_ok=True)
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
def probe(c,names):
    p=os.path.join(B,"d.cir")
    open(p,"w",encoding="latin-1").write("* op\n"+c+MODEL+"\n.control\nop\n"+
        "".join("print %s\n"%n for n in names)+"quit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","d.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    out={}
    for ln in r.stdout.splitlines():
        s=ln.strip()
        if "=" in s and s and s[0] in "vi@":
            k,v=s.split("=",1)
            try: out[k.strip()]=float(v.strip())
            except: pass
    return out
def ce(vm, rbx, rm, re1, rb1t=22e3, rb1b=4.7e3, rc=220):
    return """VCC vcc 0 5
VM mod 0 %g
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va vae %g
RM1 mod vae %g
RBX1 vae 0 %g
"""%(vm,rb1t,rb1b,rc,re1,rm,rbx)
if __name__=="__main__":
    best=None
    print("target: Ic_hi/Ic_lo = 1.6582  (m = 24.77%)")
    for re1 in (100,220):
        for rm in (6800,22000):
            for rbx in (220,470,1000,2200):
                hi=probe(ce(0.0748,rbx,rm,re1),["@qm1[ic]","v(xcn)","v(va)"])
                lo=probe(ce(4.0748,rbx,rm,re1),["@qm1[ic]","v(xcn)","v(va)"])
                ich=hi.get("@qm1[ic]",0)*1e3; icl=lo.get("@qm1[ic]",0)*1e3
                if icl<=0.05 or ich<=0: continue
                ratio=ich/icl
                vce=min(hi.get("v(xcn)",0)-hi.get("v(va)",0), lo.get("v(xcn)",0)-lo.get("v(va)",0))
                flag="<<<" if 1.45<ratio<1.90 and vce>1.5 else ""
                print("  Re1=%4g Rm=%6g Rbx=%6g -> Ic %6.3f/%6.3f mA ratio=%5.3f Vce_min=%.2f %s"%(
                    re1,rm,rbx,ich,icl,ratio,vce,flag))
                if 1.45<ratio<1.90 and vce>1.5:
                    if best is None or abs(ratio-1.658)<abs(best[3]-1.658):
                        best=(re1,rm,rbx,ratio,ich,icl)
    print("\nBEST:",best)
    json.dump({"best":best},open(os.path.join(ST,"results","emod_tune.json"),"w"),indent=1)
