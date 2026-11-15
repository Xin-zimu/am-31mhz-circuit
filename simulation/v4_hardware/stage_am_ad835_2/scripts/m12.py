# -*- coding: utf-8 -*-
"""Module 12: short-window project runs (honest, time-boxed) + envelope/FFT.
Windows chosen so a 31 MHz carrier is fully resolved and the 20 kHz modulation
is still visible: 300 us total would be ideal but B cannot complete it, so each
run uses the longest window that finishes and the window is recorded.
"""
import os, sys, re, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod12"); os.makedirs(B,exist_ok=True)
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

def xnet(u):
    a=0.1*u; b=0.4*u; R1=100e3
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(R1,R2,R3)

SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
YN="RS TP2 A 510\nRP A 0 680\n"

def build(name, model, u=1.05, tran=".tran 0 300u 200u 4n uic", opts="", tmax_ps=None):
    body = BASE+SUP+YN+xnet(u)
    if model=="A":
        body += "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n"
    else:
        body += "XAD835 XA 0 A 0 ADN A TP3 ADP AD835_BEHAV\n.include ../../adapted/AD835_Behav.sub\n"
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n"+opts+"\n"+tran+"\n.end\n")
    return p

def runto(name, model, **kw):
    p=build(name, model, **kw)
    t0=time.time()
    try: r=run(p,ascii=True,timeout=1500)
    except Exception: return None,"TIMEOUT %.0fs"%(time.time()-t0)
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    if r.returncode!=0 or sz==0:
        tl=[l for l in log(p).splitlines() if "Warning" not in l and l.strip()][-2:]
        return None,"FAIL rc=%d %.0fs %s"%(r.returncode,time.time()-t0,tl)
    return load_raw(os.path.join(B,name+".raw")),"ok %.0fs"%(time.time()-t0)

jobs=[("P_ref","P",dict(tran=".tran 0 300u 200u 4n uic")),
      ("A_510","A",dict(tran=".tran 0 300u 200u 4n uic")),
      ("B_510","B",dict(tran=".tran 0 120u 100u 0.05n uic")),
      ("B_direct","B",dict(tran=".tran 0 120u 100u 0.05n uic")),
     ]
store={}
for name,model,kw in jobs:
    if model=="P":
        p=os.path.join(B,name+".net")
        open(p,"w",encoding="utf-8").write(BASEP+".options plotwinsize=0\n"+kw["tran"]+"\n.end\n")
        t0=time.time()
        try: r=run(p,ascii=True,timeout=900)
        except Exception: print("%-9s TIMEOUT"%name,flush=True); continue
        sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
        print("%-9s %s %.0fs"%(name,"ok" if sz else "FAIL",time.time()-t0),flush=True)
        if sz: store[name]=load_raw(os.path.join(B,name+".raw"))
        continue
    R,msg=runto(name,model,**kw)
    print("%-9s %s"%(name,msg),flush=True)
    if R is not None: store[name]=R

np.savez(os.path.join(RES,"m12.npz"), **{f"{a}__{b}":v for a,d in store.items() for b,v in d.items() if b in ("time","V(tp3)","V(v1)","V(tp2)","V(a)","V(xa)")})
print("stored:", list(store.keys()))
print("DONE",flush=True)
