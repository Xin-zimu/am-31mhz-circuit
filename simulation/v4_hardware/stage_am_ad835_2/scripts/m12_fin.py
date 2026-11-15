# -*- coding: utf-8 -*-
"""Module 12 (definitive): project AM comparison, POLY vs AD835 A vs AD835 B.
Reliable settings found by scan: .tran 0 400u 300u 2n uic   (44 s, rc=0)
"""
import os, sys, re, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","fin"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")
RAW=open(NET,encoding="latin-1").read()
def base(with_poly):
    t=re.sub(r"^\.tran.*$","",RAW,flags=re.M)
    t=re.sub(r"^\.options plotwinsize.*$","",t,flags=re.M)
    t=re.sub(r"^\.end\s*$","",t,flags=re.M)
    if not with_poly:
        t=re.sub(r"^xEAM_-EAM.*$","* [POLY removed]",t,flags=re.M)
        t=re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS","",t,flags=re.M|re.S)
    return t
BASEP=base(True); BASE=base(False)
SAVE=".save V(tp3) V(v1) V(tp2) V(a) V(xa) I(VADP) I(VADN)\n"

def xnet(u):
    a=0.1*u; b=0.4*u; R1=100e3
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(R1,R2,R3)
SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"

def go(name, text, tran=".tran 0 400u 300u 2n uic", to=1500):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(text+"\n.options plotwinsize=0\n"+SAVE+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=to)
    except Exception: return None,"TIMEOUT %.0fs"%(time.time()-t0)
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    if r.returncode!=0 or sz==0:
        tl=[l for l in log(p).splitlines() if "Warning" not in l and l.strip()][-2:]
        return None,"FAIL rc=%d %.0fs %s"%(r.returncode,time.time()-t0,tl)
    return load_raw(os.path.join(B,name+".raw")),"ok %.0fs"%(time.time()-t0)

store={}
# 1 reference POLY, frozen
R,msg=go("ref_poly", BASEP); print("%-12s %s"%("ref_poly",msg),flush=True)
if R: store["ref_poly"]=R
# 2 model A with 510/680 attenuator
R,msg=go("A_510_680", BASE+SUP+"RS TP2 A 510\nRP A 0 680\n"+xnet(1.05)+
         "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n")
print("%-12s %s"%("A_510_680",msg),flush=True)
if R: store["A_510_680"]=R
# 3 model A direct (no attenuator): TP2 straight into Y1/Z
R,msg=go("A_direct", BASE+SUP+"RS TP2 A 0.001\nRP A 0 1e9\n"+xnet(1.05)+
         "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n")
print("%-12s %s"%("A_direct",msg),flush=True)
if R: store["A_direct"]=R
# 4 model A U=1.00 network
R,msg=go("A_U100", BASE+SUP+"RS TP2 A 510\nRP A 0 680\n"+xnet(1.00)+
         "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n")
print("%-12s %s"%("A_U100",msg),flush=True)
if R: store["A_U100"]=R
# 5 model B: short window (stiff internal pole)
R,msg=go("B_short", BASE+SUP+"RS TP2 A 510\nRP A 0 680\n"+xnet(1.05)+
         "XAD835 XA 0 A 0 ADN A TP3 ADP AD835_BEHAV\n.include ../../adapted/AD835_Behav.sub\n",
         tran=".tran 0 60u 50u 0.05n uic", to=1500)
print("%-12s %s"%("B_short",msg),flush=True)
if R: store["B_short"]=R

np.savez(os.path.join(RES,"fin.npz"), **{f"{a}__{b}":v for a,d in store.items() for b,v in d.items()})
json.dump({k:list(v.keys()) for k,v in store.items()}, open(os.path.join(RES,"fin_keys.json"),"w"), indent=1)
print("stored:", list(store.keys()),flush=True)
print("DONE",flush=True)
