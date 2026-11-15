# -*- coding: utf-8 -*-
"""Module 9/11: controlled project runs.
Every variant removes the POLY element (otherwise two ideal sources fight on TP3).
Runs are time-boxed; failures are recorded, not hidden.
"""
import os, sys, re, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod11"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")

RAW=open(NET,encoding="latin-1").read()
def strip_poly(t):
    t=re.sub(r"^\.tran.*$","",t,flags=re.M)
    t=re.sub(r"^\.options plotwinsize.*$","",t,flags=re.M)
    t=re.sub(r"^\.end\s*$","",t,flags=re.M)
    t=re.sub(r"^xEAM_-EAM.*$","* [POLY element removed for AD835 variant]",t,flags=re.M)
    t=re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS","",t,flags=re.M|re.S)
    return t
BASE=strip_poly(RAW)
# reference WITH poly (kept intact) for comparison
BASEP=re.sub(r"^\.tran.*$","",RAW,flags=re.M)
BASEP=re.sub(r"^\.options plotwinsize.*$","",BASEP,flags=re.M)
BASEP=re.sub(r"^\.end\s*$","",BASEP,flags=re.M)

def xnet(u):
    a=0.1*u; b=0.4*u; R1=100e3
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return ("* X network for U=%.3f : X = %.4f*Vm - %.4f\n"
            "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(u,a,b,R1,R2,R3))

SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
YN = ("* Y/Z attenuator 510/680 (stage AM-AD835.1 recommendation)\n"
      "RS TP2 A 510\nRP A 0 680\n")

def variant(name, model, u=1.05, rs=510.0, rp=680.0, opts="", tran=".tran 0 300u 200u 4n uic",
            ynet=True, timeout=900):
    body = BASE + SUP
    if ynet: body += ("RS TP2 A %g\nRP A 0 %g\n"%(rs,rp))
    else:    body += "RS TP2 A 0.001\nRP A 0 1e9\n"
    body += xnet(u)
    if model=="A":
        body += "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n"
    else:
        body += "XAD835 XA 0 A 0 ADN A TP3 ADP AD835_BEHAV\n.include ../../adapted/AD835_Behav.sub\n"
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n"+opts+"\n"+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=timeout)
    except Exception: 
        return name,None,"TIMEOUT(%ds)"%(time.time()-t0)
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    dt=time.time()-t0
    if r.returncode!=0 or sz==0:
        tail=[l for l in log(p).splitlines() if "Warning" not in l][-3:]
        return name,None,"rc=%d %.0fs size=%d %s"%(r.returncode,dt,sz,tail)
    return name,load_raw(os.path.join(B,name+".raw")),"ok %.0fs"%(dt)

results={}
JOBS=[
 ("ref_poly",   "P", 1.05, "",           ".tran 0 300u 200u 4n uic"),
 ("A_510_680",  "A", 1.05, "",           ".tran 0 300u 200u 4n uic"),
 ("A_direct",   "A", 1.05, "",           ".tran 0 300u 200u 4n uic"),
 ("B_510_680",  "B", 1.05, "",           ".tran 0 300u 200u 4n uic"),
 ("B_510_680_g","B", 1.05, ".options method=gear cshunt=1p reltol=1e-3", ".tran 0 120u 70u 4n uic"),
 ("A_510_680_g","A", 1.05, ".options method=gear cshunt=1p reltol=1e-3", ".tran 0 120u 70u 4n uic"),
]
for name, model, u, opts, tran in JOBS:
    if model=="P":
        p=os.path.join(B,name+".net")
        open(p,"w",encoding="utf-8").write(BASEP+".options plotwinsize=0\n"+tran+"\n.end\n")
        t0=time.time()
        try: r=run(p,ascii=True,timeout=600)
        except Exception: print("%-14s TIMEOUT"%name,flush=True); continue
        ok = r.returncode==0 and os.path.getsize(os.path.join(B,name+".raw"))>0
        print("%-14s %s %.0fs"%(name,"ok" if ok else "FAIL",time.time()-t0),flush=True)
        continue
    nm,R,msg = variant(name,model,u,opts=opts,tran=tran,
                       ynet=(name!="A_direct"))
    print("%-14s %s"%(nm,msg),flush=True)
    if R is not None:
        np.savez(os.path.join(B,nm+"_s.npz"), **{k:v for k,v in R.items()})
print("DONE",flush=True)
